import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import app.models.entities  # noqa: E402,F401 确保模型在 Base.metadata 注册（任何测试先跑都建全表）
import pytest


@pytest.fixture
def db_session(tmp_path):
    """独立 SQLite 文件库，每测试一个。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base

    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine)
    s = S()
    yield s
    s.close()


@pytest.fixture
def client(tmp_path):
    from fastapi.testclient import TestClient
    from app.core.config import make_settings
    from app.main import create_app

    app = create_app(make_settings(str(tmp_path)))
    with TestClient(app) as c:
        yield c
