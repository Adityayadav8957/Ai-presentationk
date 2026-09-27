from sqlmodel import Session, select

from app.agents.image_agent import ImageAgent
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


def _job_for(session: Session, task_id: str) -> Job | None:
    return session.exec(select(Job).where(Job.celery_task_id == task_id)).first()


def _ensure_ollama_ready(presentation: Presentation, on_progress) -> None:
    if presentation.llm_provider == "ollama" and presentation.llm_model:
        on_progress("pulling_model")
        ensure_model_pulled(presentation.llm_model)


def _fail_job(session: Session, job: Job | None, presentation: Presentation, exc: Exception) -> None:
    if job:
        job.status = "failed"
        job.step = "error"
        job.error = str(exc)
        session.add(job)
    presentation.status = "failed"
    session.add(presentation)
    session.commit()


def _run_qa(session: Session, presentation_id: str, slides: list[Slide], llm_provider_name: str | None) -> None:
    qa_agent = QAAgent(get_vision_provider(llm_provider_name))
    for slide in slides:
        slide.qa_report = qa_agent.review(presentation_id, slide.id)
        session.add(slide)
    session.commit()


@celery_app.task(bind=True, name="generate_presentation")
def generate_presentation(self, presentation_id: str) -> str:
    with Session(engine) as session:
        presentation = session.get(Presentation, presentation_id)
        if presentation is None:
            raise ValueError(f"Presentation {presentation_id} not found")

        job = _job_for(session, self.request.id)

        def on_progress(step: str) -> None:
            self.update_state(state="PROGRESS", meta={"step": step})
            if job:
                job.step = step
                session.add(job)
                session.commit()

        try:
            _ensure_ollama_ready(presentation, on_progress)

            orchestrator = Orchestrator(
                llm_provider_name=presentation.llm_provider,
                llm_model_name=presentation.llm_model,
                image_provider_name=presentation.image_provider,
            )
            result = orchestrator.run(presentation.brief, presentation.id, on_progress=on_progress)

            presentation.story = {"outline": result["story"]}
            presentation.theme = result["theme"]
            presentation.status = "ready"
            session.add(presentation)
            session.commit()

            slides: list[Slide] = []
            for position, content in enumerate(result["slides"]):
                slide = Slide(presentation_id=presentation.id, position=position, content=content)
                session.add(slide)
                slides.append(slide)
            session.commit()
            for slide in slides:
                session.refresh(slide)

            on_progress("qa")
            _run_qa(session, presentation.id, slides, presentation.llm_provider)

            if job:
                job.status = "done"
                job.step = "final"
                session.add(job)
            session.commit()
        except Exception as exc:
            _fail_job(session, job, presentation, exc)
            raise

    return presentation_id


@celery_app.task(bind=True, name="refine_presentation")
def refine_presentation(self, presentation_id: str, instruction: str) -> str:
    with Session(engine) as session:
        presentation = session.get(Presentation, presentation_id)
        if presentation is None:
            raise ValueError(f"Presentation {presentation_id} not found")

        job = _job_for(session, self.request.id)

        def on_progress(step: str) -> None:
            self.update_state(state="PROGRESS", meta={"step": step})
            if job:
                job.step = step
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

            on_progress("image_generation")
            image_agent = ImageAgent(get_image_provider(presentation.image_provider))
            revised = image_agent.run(revised, presentation.id)

            for slide in existing:
                session.delete(slide)
            session.commit()

            new_slides: list[Slide] = []
            for position, content in enumerate(revised):
                slide = Slide(presentation_id=presentation.id, position=position, content=content)
                session.add(slide)
                new_slides.append(slide)
            session.commit()
            for slide in new_slides:
                session.refresh(slide)

            on_progress("qa")
            _run_qa(session, presentation.id, new_slides, presentation.llm_provider)

            session.add(
                Message(presentation_id=presentation_id, role="assistant", content="Updated the presentation.")
            )

            if job:
                job.status = "done"
                job.step = "final"
                session.add(job)
            session.commit()
        except Exception as exc:
            _fail_job(session, job, presentation, exc)
            raise

    return presentation_id
