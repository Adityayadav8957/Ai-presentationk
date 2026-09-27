from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models.message import Message
from app.models.presentation import Presentation

router = APIRouter(prefix="/presentations/{presentation_id}/chat", tags=["chat"])


@router.post("")
def send_message(presentation_id: str, payload: dict, session: Session = Depends(get_session)):
    presentation = session.get(Presentation, presentation_id)
    if presentation is None:
        return {"error": "presentation not found"}

    session.add(Message(presentation_id=presentation_id, role="user", content=payload["content"]))
    session.commit()

    return {"status": "queued", "message": "Refinement pipeline not yet implemented."}
