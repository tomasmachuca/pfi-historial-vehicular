from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.config import settings

_engine_kw: dict = {"pool_pre_ping": True}
if (addr := (settings.DATABASE_HOSTADDR or "").strip()):
    _engine_kw["connect_args"] = {"hostaddr": addr}

engine = create_engine(settings.DATABASE_URL, **_engine_kw)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
