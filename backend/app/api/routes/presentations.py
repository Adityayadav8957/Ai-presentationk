from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.job import Job
from app.models.presentation import Presentation
from app.models.slide import Slide
from app.worker.tasks import generate_presentation

router = APIRouter(prefix="/presentations", tags=["presentations"])


@router.post("")
def create_presentation(payload: dict, session: Session = Depends(get_session)):
    llm_provider = payload.pop("llm_provider", None)
    llm_model = payload.pop("llm_model", None)
    image_provider = payload.pop("image_provider", None)

    presentation = Presentation(
        title=payload.get("topic", "Untitled"),
        brief=payload,
        llm_provider=llm_provider,
        llm_model=llm_model,
        image_provider=image_provider,
    )
    session.add(presentation)
    session.commit()
    session.refresh(presentation)

    task = generate_presentation.delay(presentation.id)

    job = Job(presentation_id=presentation.id, celery_task_id=task.id)
    session.add(job)
    session.commit()

    return {"presentation_id": presentation.id, "job_id": job.id}


@router.get("")
def list_presentations(session: Session = Depends(get_session)):
    return session.exec(select(Presentation)).all()


@router.get("/{presentation_id}")
def get_presentation(presentation_id: str, session: Session = Depends(get_session)):
    presentation = session.get(Presentation, presentation_id)
    slides = session.exec(
        select(Slide).where(Slide.presentation_id == presentation_id).order_by(Slide.position)
    ).all()
    return {"presentation": presentation, "slides": slides}


@router.get("/{presentation_id}/status")
def get_status(presentation_id: str, session: Session = Depends(get_session)):
    return session.exec(
        select(Job)
        .where(Job.presentation_id == presentation_id)
        .order_by(Job.created_at.desc())
    ).first()
