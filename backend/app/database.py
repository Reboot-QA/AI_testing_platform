from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_database_url = settings.sqlalchemy_database_url

_engine_kwargs: dict = {}
_connect_args: dict = {}

if _database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
elif _database_url.startswith("mysql"):
    _engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    }

engine = create_engine(
    _database_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
