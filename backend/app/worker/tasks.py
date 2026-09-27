from sqlmodel import Session, select

from app.agents.orchestrator import Orchestrator
from app.db.session import engine
from app.models.job import Job
from app.models.presentation import Presentation
from app.models.slide import Slide
from app.worker.celery_app import celery_app


@celery_app.task(bind=True, name="generate_presentation")
def generate_presentation(self, presentation_id: str) -> str:
    with Session(engine) as session:
        presentation = session.get(Presentation, presentation_id)
        if presentation is None:
            raise ValueError(f"Presentation {presentation_id} not found")

        job = session.exec(
            select(Job).where(Job.celery_task_id == self.request.id)
        ).first()

        def on_progress(step: str) -> None:
            self.update_state(state="PROGRESS", meta={"step": step})
            if job:
                job.step = step
                session.add(job)
                session.commit()

        orchestrator = Orchestrator(llm_provider_name=presentation.llm_provider)
        result = orchestrator.run(presentation.brief, on_progress=on_progress)

        presentation.story = result["story"]
        presentation.status = "ready"
        session.add(presentation)

        for position, slide_content in enumerate(result["slides"]):
            session.add(
                Slide(presentation_id=presentation.id, position=position, content=slide_content)
            )

        if job:
            job.status = "done"
            job.step = "final"
            session.add(job)

        session.commit()

    return presentation_id
