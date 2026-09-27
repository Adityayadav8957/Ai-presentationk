from datetime import datetime
from uuid import uuid4

from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    presentation_id: str = Field(foreign_key="presentation.id", index=True)
    celery_task_id: str
    status: str = Field(default="queued")
    step: str = Field(default="queued")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
