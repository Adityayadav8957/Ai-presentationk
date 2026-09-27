from datetime import datetime
from uuid import uuid4

from sqlmodel import JSON, Column, Field, SQLModel


class Presentation(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    title: str
    brief: dict = Field(default_factory=dict, sa_column=Column(JSON))
    theme: dict = Field(default_factory=dict, sa_column=Column(JSON))
    story: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = Field(default="draft")
    llm_provider: str | None = None
    image_provider: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
