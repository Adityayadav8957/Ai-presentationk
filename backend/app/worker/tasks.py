import logging
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.agents.design_agent import design_theme_question
from app.agents.orchestrator import Orchestrator
from app.agents.qa_agent import QAAgent
from app.agents.revision_agent import RevisionAgent
from app.db.session import engine
from app.models.job import Job
from app.models.message import Message
from app.models.presentation import Presentation
from app.models.slide import Slide
from app.providers.image.registry import get_image_provider
from app.providers.llm.ollama_utils import ensure_model_pulled
from app.providers.llm.registry import get_llm_provider, get_vision_provider
from app.worker.celery_app import celery_app
from app.worker.slide_pipeline import render_slides_in_parallel

logger = logging.getLogger(__name__)


def _job_for(session: Session, task_id: str) -> Job | None:
    return session.exec(select(Job).where(Job.celery_task_id == task_id)).first()


def _ensure_ollama_ready(presentation: Presentation, on_progress) -> None:
    if presentation.llm_provider == "ollama" and presentation.llm_model:
        on_progress("pulling_model")
        ensure_model_pulled(presentation.llm_model)


def _fail_job(session: Session, job: Job | None, presentation: Presentation, exc: Exception) -> None:
    logger.error("Task failed for presentation=%s: %s", presentation.id, exc)
    if job:
        job.status = "failed"
        job.step = "error"
        job.error = str(exc)
        job.updated_at = datetime.now(UTC)
        session.add(job)
    presentation.status = "failed"
    session.add(presentation)
    session.commit()


def _persist_bare_slides(session: Session, presentation_id: str, slides: list[dict]) -> list[Slide]:
    """Writes each slide's semantic content immediately — visible to the
    frontend right away, even before images/HTML exist for any of them."""
    rows: list[Slide] = []
    for position, content in enumerate(slides):
        slide = Slide(presentation_id=presentation_id, position=position, content=content)
        session.add(slide)
        rows.append(slide)
    session.commit()
    for slide in rows:
        session.refresh(slide)
    return rows


@celery_app.task(bind=True, name="generate_presentation")
def generate_presentation(self, presentation_id: str) -> str:
    logger.info("generate_presentation: starting presentation=%s task=%s", presentation_id, self.request.id)
    with Session(engine) as session:
        presentation = session.get(Presentation, presentation_id)
        if presentation is None:
            raise ValueError(f"Presentation {presentation_id} not found")

        job = _job_for(session, self.request.id)

        def on_progress(step: str) -> None:
            logger.info("generate_presentation: presentation=%s step=%s", presentation_id, step)
            if job:
                job.step = step
                job.updated_at = datetime.now(UTC)
                session.add(job)
                session.commit()

        try:
            _ensure_ollama_ready(presentation, on_progress)

            existing_slides = session.exec(
                select(Slide).where(Slide.presentation_id == presentation_id).order_by(Slide.position)
            ).all()

            llm_provider_name = presentation.llm_provider

            if existing_slides:
                # Resuming after a guided-mode pause (e.g. design confirmation) —
                # planning already ran and its output is already persisted.
                logger.info(
                    "generate_presentation: resuming presentation=%s with %d planned slides",
                    presentation_id,
                    len(existing_slides),
                )
                slides = existing_slides
                llm = get_llm_provider(llm_provider_name, presentation.llm_model)
            else:
                orchestrator = Orchestrator(
                    llm_provider_name=llm_provider_name,
                    llm_model_name=presentation.llm_model,
                )
                result = orchestrator.run(presentation.brief, on_progress=on_progress)

                presentation.story = {"outline": result["story"]}
                presentation.theme = result["theme"]

                if presentation.guided_mode:
                    on_progress("needs_input")
                    presentation.status = "needs_input"
                    presentation.pending_questions = {
                        "stage": "post_planning",
                        "questions": [design_theme_question(result["theme"]["name"])],
                    }
                    session.add(presentation)
                    session.commit()

                    # Persist the planned slides now so resuming skips planning
                    # entirely — only the per-slide render step runs afterward.
                    _persist_bare_slides(session, presentation.id, result["slides"])

                    if job:
                        job.status = "waiting_for_input"
                        job.step = "needs_input"
                        job.updated_at = datetime.now(UTC)
                        session.add(job)
                    session.commit()
                    logger.info(
                        "generate_presentation: paused for design confirmation presentation=%s",
                        presentation_id,
                    )
                    return presentation_id

                presentation.status = "ready"
                session.add(presentation)
                session.commit()

                on_progress("rendering_slides")
                slides = _persist_bare_slides(session, presentation.id, result["slides"])
                llm = orchestrator.llm

            qa_agent = QAAgent(get_vision_provider(llm_provider_name)) if presentation.qa_enabled else None
            render_slides_in_parallel(
                presentation_id=presentation.id,
                slides=slides,
                theme=presentation.theme or {},
                brief=presentation.brief,
                image_provider=get_image_provider(presentation.image_provider),
                llm=llm,
                qa_agent=qa_agent,
                job_id=job.id if job else None,
            )

            if job:
                job.status = "done"
                job.step = "final"
                job.updated_at = datetime.now(UTC)
                session.add(job)
            session.commit()
            logger.info("generate_presentation: done presentation=%s (%d slides)", presentation_id, len(slides))
        except Exception as exc:
            _fail_job(session, job, presentation, exc)
            raise

    return presentation_id


@celery_app.task(bind=True, name="refine_presentation")
def refine_presentation(self, presentation_id: str, instruction: str) -> str:
    logger.info(
        "refine_presentation: starting presentation=%s task=%s instruction=%r",
        presentation_id,
        self.request.id,
        instruction,
    )
    with Session(engine) as session:
        presentation = session.get(Presentation, presentation_id)
        if presentation is None:
            raise ValueError(f"Presentation {presentation_id} not found")

        job = _job_for(session, self.request.id)

        def on_progress(step: str) -> None:
            logger.info("refine_presentation: presentation=%s step=%s", presentation_id, step)
            if job:
                job.step = step
                job.updated_at = datetime.now(UTC)
                session.add(job)
                session.commit()

        try:
            _ensure_ollama_ready(presentation, on_progress)

            on_progress("understanding_request")
            existing = session.exec(
                select(Slide).where(Slide.presentation_id == presentation_id).order_by(Slide.position)
            ).all()
            current_content = [s.content for s in existing]

            llm = get_llm_provider(presentation.llm_provider, presentation.llm_model)

            on_progress("revising")
            revised = RevisionAgent(llm).run(current_content, instruction)

            for slide in existing:
                session.delete(slide)
            session.commit()

            on_progress("rendering_slides")
            slides = _persist_bare_slides(session, presentation.id, revised)

            qa_agent = QAAgent(get_vision_provider(presentation.llm_provider)) if presentation.qa_enabled else None
            render_slides_in_parallel(
                presentation_id=presentation.id,
                slides=slides,
                theme=presentation.theme or {},
                brief=presentation.brief,
                image_provider=get_image_provider(presentation.image_provider),
                llm=llm,
                qa_agent=qa_agent,
                job_id=job.id if job else None,
            )

            session.add(
                Message(presentation_id=presentation_id, role="assistant", content="Updated the presentation.")
            )

            if job:
                job.status = "done"
                job.step = "final"
                job.updated_at = datetime.now(UTC)
                session.add(job)
            session.commit()
            logger.info("refine_presentation: done presentation=%s", presentation_id)
        except Exception as exc:
            _fail_job(session, job, presentation, exc)
            raise

    return presentation_id
