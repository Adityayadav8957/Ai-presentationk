from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, echo=False)


def init_db() -> None:
    from app.models import job, message, presentation, slide  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
