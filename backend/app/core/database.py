from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None


def init_engine(db_url: str) -> None:
    """按需初始化引擎并建表（幂等）。"""
    global _engine, _SessionLocal
    _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(bind=_engine)
    Base.metadata.create_all(_engine)


def get_session_local():
    if _SessionLocal is None:
        raise RuntimeError("engine 未初始化：请先调用 init_engine")
    return _SessionLocal()


def get_db():
    db = get_session_local()
    try:
        yield db
    finally:
        db.close()
