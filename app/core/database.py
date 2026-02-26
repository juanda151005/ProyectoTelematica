from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.shared.base_model import Base

settings = get_settings()

connect_args = {}
if settings.database_url.startswith('sqlite'):
    connect_args = {'check_same_thread': False}

engine = create_engine(settings.database_url, echo=False, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_db_and_tables() -> None:
    # Importa modelos para que SQLAlchemy registre todas las tablas.
    from app.core import model_registry  # noqa: F401

    Base.metadata.create_all(bind=engine)
