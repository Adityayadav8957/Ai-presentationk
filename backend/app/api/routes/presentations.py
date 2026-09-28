from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.agents.design_agent import THEMES
from app.agents.requirements_agent import RequirementsAgent
from app.db.session import get_session
from app.models.job import Job
from app.models.presentation import Presentation
from app.models.slide import Slide
from app.providers.llm.registry import get_llm_provider
from app.worker.celery_app import celery_app
from app.worker.tasks import generate_presentation

router = APIRouter(prefix="/presentations", tags=["presentations"])

TERMINAL_JOB_STATUSES = ("done", "failed", "cancelled")

# waiting_for_input isn't a traditional terminal state (the job can still be
# resumed once answered), but it's also not something the staleness check
# should ever fail — the task has already finished and is deliberately
# waiting on a human, for however long that takes. It stays cancellable
# though, so it's kept separate from TERMINAL_JOB_STATUSES above.
STALENESS_EXEMPT_STATUSES = (*TERMINAL_JOB_STATUSES, "waiting_for_input")

# A single LLM call (e.g. planning 10 slides on a slow local CPU model) can
# legitimately take longer than this — so once we're past it, we don't just
# assume the worker died, we actually check with Celery whether the task is
# still running (see _is_task_active). Only if it's confirmed NOT running do
# we mark the job failed early. HARD_STALE_TIMEOUT is a fallback ceiling in
# case the liveness check itself can't be trusted (e.g. broker hiccup).
SOFT_STALE_TIMEOUT = timedelta(minutes=3)
HARD_STALE_TIMEOUT = timedelta(minutes=20)


def _as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _is_task_active(task_id: str) -> bool | None:
    """Best-effort check via Celery's control/inspect API.
    True/False = confirmed alive/dead. None = couldn't tell (e.g. a broker
    hiccup) — callers should treat that as "not confirmed dead", relying on
    HARD_STALE_TIMEOUT as the backstop instead of failing the job early."""
    try:
        active = celery_app.control.inspect(timeout=2).active()
        if active is None:
            return None
        return any(task.get("id") == task_id for tasks in active.values() for task in tasks)
    except Exception:
        return None


@router.post("")
def create_presentation(payload: dict, session: Session = Depends(get_session)):
    llm_provider = payload.pop("llm_provider", None)
    llm_model = payload.pop("llm_model", None)
    image_provider = payload.pop("image_provider", None)
    qa_enabled = bool(payload.pop("qa_enabled", False))
    guided_mode = bool(payload.pop("guided_mode", False))

    presentation = Presentation(
        title=payload.get("topic", "Untitled"),
        brief=payload,
        llm_provider=llm_provider,
        llm_model=llm_model,
        image_provider=image_provider,
        qa_enabled=qa_enabled,
        guided_mode=guided_mode,
    )
    session.add(presentation)
    session.commit()
    session.refresh(presentation)

    if guided_mode:
        llm = get_llm_provider(llm_provider, llm_model)
        questions = RequirementsAgent(llm).run(presentation.brief)
        if questions:
            presentation.status = "needs_input"
            presentation.pending_questions = {"stage": "pre_flight", "questions": questions}
            session.add(presentation)
            session.commit()
            return {"presentation_id": presentation.id, "needs_input": True, "questions": questions}

    task = generate_presentation.delay(presentation.id)

    job = Job(presentation_id=presentation.id, celery_task_id=task.id)
    session.add(job)
    session.commit()

    return {"presentation_id": presentation.id, "job_id": job.id}


@router.post("/{presentation_id}/answer")
def answer_questions(presentation_id: str, payload: dict, session: Session = Depends(get_session)):
    presentation = session.get(Presentation, presentation_id)
    if presentation is None:
        return {"error": "presentation not found"}
    if not presentation.pending_questions:
        return {"error": "no pending questions for this presentation"}

    stage = presentation.pending_questions.get("stage")
    answers = payload.get("answers", {})

    if stage == "pre_flight":
        presentation.brief = {**presentation.brief, "clarifications": answers}
        presentation.status = "draft"
    elif stage == "post_planning":
        chosen = answers.get("theme")
        if chosen in THEMES:
            presentation.theme = {"name": chosen, **THEMES[chosen]}
        presentation.status = "ready"
    else:
        return {"error": f"unknown clarification stage: {stage}"}

    presentation.pending_questions = None
    session.add(presentation)
    session.commit()

    # For post_planning, generate_presentation sees the already-persisted
    # bare slides and resumes straight into per-slide rendering instead of
    # re-running research/story/planning from scratch.
    task = generate_presentation.delay(presentation.id)
    job = Job(presentation_id=presentation.id, celery_task_id=task.id)
    session.add(job)
    session.commit()

    return {"job_id": job.id}


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
    job = session.exec(
        select(Job)
        .where(Job.presentation_id == presentation_id)
        .order_by(Job.created_at.desc())
    ).first()

    if job and job.status not in STALENESS_EXEMPT_STATUSES:
        age = datetime.now(UTC) - _as_utc(job.updated_at)
        should_fail = False
        reason = None

        if age > HARD_STALE_TIMEOUT:
            should_fail = True
            reason = "This job made no progress for a long time and was stopped."
        elif age > SOFT_STALE_TIMEOUT:
            liveness = _is_task_active(job.celery_task_id)
            if liveness is False:
                should_fail = True
                reason = (
                    "This job stalled with no progress for a while — the worker likely "
                    "restarted or crashed mid-task. Try generating again."
                )
            # liveness True or None (unknown) → a slow-but-alive task (e.g. a
            # big local model on CPU); keep waiting rather than fail early.

        if should_fail:
            job.status = "failed"
            job.step = "error"
            job.error = reason
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()

    return job


@router.post("/{presentation_id}/cancel")
def cancel_presentation(presentation_id: str, session: Session = Depends(get_session)):
    job = session.exec(
        select(Job)
        .where(Job.presentation_id == presentation_id)
        .order_by(Job.created_at.desc())
    ).first()

    if job is None:
        return {"error": "no job found for this presentation"}
    if job.status in TERMINAL_JOB_STATUSES:
        return {"status": job.status}

    # terminate=True actually kills the worker process running this task
    # (not just marks it revoked) — a plain revoke without terminate only
    # stops a task that hasn't started yet.
    celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")

    job.status = "cancelled"
    job.step = "cancelled"
    job.error = "Cancelled by user."
    job.updated_at = datetime.now(UTC)
    session.add(job)

    presentation = session.get(Presentation, presentation_id)
    if presentation:
        presentation.status = "cancelled"
        presentation.pending_questions = None
        session.add(presentation)

    session.commit()
    return {"status": "cancelled"}


@router.post("/{presentation_id}/retry")
def retry_presentation(presentation_id: str, session: Session = Depends(get_session)):
    presentation = session.get(Presentation, presentation_id)
    if presentation is None:
        return {"error": "presentation not found"}

    for slide in session.exec(select(Slide).where(Slide.presentation_id == presentation_id)).all():
        session.delete(slide)
    presentation.status = "draft"
    presentation.pending_questions = None
    session.add(presentation)
    session.commit()

    task = generate_presentation.delay(presentation.id)

    job = Job(presentation_id=presentation.id, celery_task_id=task.id)
    session.add(job)
    session.commit()

    return {"presentation_id": presentation.id, "job_id": job.id}
