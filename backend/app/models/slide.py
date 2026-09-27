from uuid import uuid4

from sqlmodel import JSON, Column, Field, SQLModel


class Slide(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    presentation_id: str = Field(foreign_key="presentation.id", index=True)
    position: int
    content: dict = Field(default_factory=dict, sa_column=Column(JSON))
    qa_report: dict = Field(default_factory=dict, sa_column=Column(JSON))
