import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

from sqlmodel import Session

from app.agents.html_agent import HTMLAgent
from app.agents.image_agent import ImageAgent
from app.agents.qa_agent import QAAgent
from app.db.session import engine
from app.models.job import Job
from app.models.slide import Slide
from app.providers.image.base import ImageProvider
from app.providers.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _process_one_slide(
    presentation_id: str,
    slide_id: str,
    position: int,
    content: dict,
    theme: dict,
    brief: dict,
    image_provider: ImageProvider,
    llm: LLMProvider,
    qa_agent: QAAgent | None,
    job_id: str | None,
) -> None:
    """Generates this slide's image(s) and HTML, then checkpoints it to
    Postgres immediately — independent of every other slide, and using its
    own DB session since this runs in a worker thread. A failure here is
    caught and logged, never raised, so one bad slide can't take down the
    rest of the deck."""
    try:
        content = ImageAgent(image_provider).run_one(content, presentation_id, position)
        content = HTMLAgent(llm).render_one(position, content, theme, brief)
    except Exception:
        logger.exception(
            "slide_pipeline: unexpected failure rendering presentation=%s position=%s",
            presentation_id,
            position,
        )

    with Session(engine) as session:
        slide = session.get(Slide, slide_id)
        if slide is not None:
            slide.content = content
            session.add(slide)
            session.commit()

        if qa_agent is not None:
            qa_report = qa_agent.review(presentation_id, slide_id)
            if slide is not None:
                slide.qa_report = qa_report
                session.add(slide)
                session.commit()

        # Bumping the job here (not just at the top-level step) means a
        # deck with many slides can't trip the staleness check just because
        # no single slide has finished yet within the timeout window.
        if job_id:
            job = session.get(Job, job_id)
            if job is not None:
                job.updated_at = datetime.now(UTC)
                session.add(job)
                session.commit()

    logger.info("slide_pipeline: presentation=%s position=%s checkpointed", presentation_id, position)


def render_slides_in_parallel(
    presentation_id: str,
    slides: list[Slide],
    theme: dict,
    brief: dict,
    image_provider: ImageProvider,
    llm: LLMProvider,
    qa_agent: QAAgent | None,
    job_id: str | None,
    max_workers: int = 4,
) -> None:
    """Renders every slide's image+HTML (and QA, if enabled) concurrently.
    Each slide is committed to the database the moment it finishes — the
    frontend (which polls the presentation while a job is running) sees
    slides appear one at a time rather than all at once at the end."""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [
            pool.submit(
                _process_one_slide,
                presentation_id,
                slide.id,
                slide.position,
                slide.content,
                theme,
                brief,
                image_provider,
                llm,
                qa_agent,
                job_id,
            )
            for slide in slides
        ]
        for future in as_completed(futures):
            future.result()
