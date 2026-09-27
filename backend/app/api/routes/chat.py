from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.job import Job
from app.models.message import Message
from app.models.presentation import Presentation
from app.worker.tasks import refine_presentation

router = APIRouter(prefix="/presentations/{presentation_id}/chat", tags=["chat"])


@router.post("")
def send_message(presentation_id: str, payload: dict, session: Session = Depends(get_session)):
    presentation = session.get(Presentation, presentation_id)
    if presentation is None:
        return {"error": "presentation not found"}

    session.add(Message(presentation_id=presentation_id, role="user", content=payload["content"]))
    session.commit()

    task = refine_presentation.delay(presentation_id, payload["content"])
    job = Job(presentation_id=presentation_id, celery_task_id=task.id)
    session.add(job)
    session.commit()

    return {"job_id": job.id}


@router.get("")
def list_messages(presentation_id: str, session: Session = Depends(get_session)):
    return session.exec(
        select(Message)
        .where(Message.presentation_id == presentation_id)
        .order_by(Message.created_at)
    ).all()
