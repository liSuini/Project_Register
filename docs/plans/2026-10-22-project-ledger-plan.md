# 项目台账系统实施计划（Implementation Plan）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付本机运行的"一个项目一本账"台账系统：9 阶段锚点树 + 自由阶段流转 + 采购/验收明细 + 附件归档 + 三口径统计导出。

**Architecture:** FastAPI 薄路由 + services 深模块（storage/tree/project/detail/stats），SQLite + 本地文件系统存附件；Vue3 SPA 三页面（列表/详情一账/统计）。架构见 `docs/specs/2026-10-22-architecture-design.md`。

**Tech Stack:** Python 3.14 (D:\developTools\python\python3.14.5) + FastAPI + SQLAlchemy + SQLite + openpyxl；Vue3 + Vite5 + Element Plus + axios。

**Spec:** `docs/specs/2026-10-22-technical-spec.md`（实现决策以技术规格为准；术语以 CONTEXT.md 为准）

## Global Constraints

- 阶段集合固定：`["商机","中标","签约","立项","采购","实施","交付","验收","结算"]`（9 个，勿增删改序）。
- 金额：数据库一律存**元**（Numeric(14,2)/Decimal）；前端交互一律**万元**（输入×10000、显示÷10000）。
- 错误契约：统一 JSON `{code, message}`；404 not_found / 409 conflict / 422 invalid。
- 服务层抛领域异常（NotFoundError/ConflictError/InvalidError，定义于 `app/errors.py`），路由层不写业务逻辑。
- 附件物理名=uuid（original_name 仅展示）；上传=先存文件后写库；删除=先删记录后删文件，物理缺失容忍。
- 非空节点（有子环节或附件）禁删（Conflict）；锚点不可删不可改名。
- 端口：后端 8000，前端 3000（Vite 代理 /api → 8000）。
- Python 命令：`python -X utf8 -m pytest ...`；依赖安装 `python -m pip install -r backend/requirements.txt`。
- 无登录、无权限；CORS 全开（本机工具）。
- 每个任务完成即 `git commit`；提交信息格式 `feat/fix/docs: <中文描述>`。
- 测试目录 `backend/tests/`；前端验证用浏览器目检（个人工具，不铺 e2e）。

## 文件结构（锁定）

```
backend/
├── requirements.txt
├── app/
│   ├── __init__.py
│   ├── main.py                      # create_app 工厂 + 路由注册 + 异常处理
│   ├── errors.py                    # AppError 家族
│   ├── core/{__init__,config,database,constants}.py  # STAGES / Settings / Base+engine / 
│   ├── models/{__init__,entities}.py
│   ├── schemas/{__init__,dtos}.py
│   ├── services/{__init__,storage,tree_service,project_service,detail_service,stats_service}.py
│   └── api/{__init__,deps,projects,nodes,attachments,purchases,acceptances,stats}.py
└── tests/{conftest,test_storage,test_tree_service,test_project_service,test_detail_service,test_stats_service,test_api_smoke}.py
frontend/
├── package.json  vite.config.js  index.html
└── src/
    ├── main.js  App.vue  router.js
    ├── api/index.js                   # axios + 各资源封装 + 金额换算
    ├── views/{ProjectList,ProjectDetail,StatsView}.vue
    └── components/{StageStepper,NodeTreePanel,DetailTables}.vue
start.ps1                               # 一键启动（Task 13）
data/                                   # 运行时生成（.gitignore 已排除）
```

---

### Task 1: 后端骨架（配置/数据库/错误/常量/应用工厂）

**Files:**
- Create: `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/core/__init__.py`, `backend/app/core/constants.py`, `backend/app/core/config.py`, `backend/app/core/database.py`, `backend/app/errors.py`, `backend/app/main.py`, `backend/tests/conftest.py`, `backend/tests/test_api_smoke.py`

**Interfaces:**
- Consumes: 无（首个任务）
- Produces: `STAGES`（list[str]，9 阶段）；`make_settings(data_dir=None) -> Settings`（含 `.data_dir/.db_path/.db_url/.upload_root`）；`init_engine(db_url)`、`get_db()`（FastAPI 依赖）、`Base`、`get_db_session_local()`；`NotFoundError/ConflictError/InvalidError`（AppError 家族，属性 `.status_code/.code/.message`）；`create_app(settings=None) -> FastAPI`（含 `GET /api/health`）

- [ ] **Step 1: 写 requirements.txt 并安装依赖**

```
fastapi
uvicorn[standard]
sqlalchemy
pydantic
python-multipart
openpyxl
pytest
httpx
```

Run: `python -m pip install -r backend/requirements.txt`
Expected: 全部安装成功

- [ ] **Step 2: 写核心模块**

`backend/app/core/constants.py`:
```python
STAGES = ["商机", "中标", "签约", "立项", "采购", "实施", "交付", "验收", "结算"]
```

`backend/app/core/config.py`:
```python
import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

@dataclass
class Settings:
    data_dir: Path
    @property
    def db_path(self) -> Path: return self.data_dir / "ledger.db"
    @property
    def db_url(self) -> str: return f"sqlite:///{self.db_path}"
    @property
    def upload_root(self) -> Path: return self.data_dir / "uploads"

def make_settings(data_dir: str | None = None) -> Settings:
    dd = data_dir or os.environ.get("LEDGER_DATA_DIR", str(BACKEND_ROOT / "data"))
    return Settings(data_dir=Path(dd))
```

`backend/app/core/database.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()
_engine = None
_SessionLocal = None

def init_engine(db_url: str):
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
```

`backend/app/errors.py`:
```python
class AppError(Exception):
    status_code = 500
    def __init__(self, message: str, code: str = "error"):
        self.message = message
        self.code = code

class NotFoundError(AppError):
    status_code = 404
    def __init__(self, message="资源不存在"): super().__init__(message, "not_found")

class ConflictError(AppError):
    status_code = 409
    def __init__(self, message="状态冲突"): super().__init__(message, "conflict")

class InvalidError(AppError):
    status_code = 422
    def __init__(self, message="参数非法"): super().__init__(message, "invalid")
```

`backend/app/main.py`:
```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import Settings, make_settings
from app.core.database import Base, init_engine
from app.errors import AppError

def create_app(settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = make_settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    init_engine(settings.db_url)

    app = FastAPI(title="Project Ledger API")
    app.state.settings = settings
    app.add_middleware(CORSMiddleware, allow_origins=["*"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code,
                            content={"code": exc.code, "message": exc.message})

    @app.get("/api/health")
    def health(): return {"status": "ok"}

    return app

app = create_app()
```

- [ ] **Step 3: 写冒烟测试**

`backend/tests/conftest.py`:
```python
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest

@pytest.fixture
def db_session(tmp_path):
    """独立 SQLite 文件库，每测试一个。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}",
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
```

`backend/tests/test_api_smoke.py`:
```python
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_app_error_contract(client):
    """409 错误契约：{code, message}。"""
    from app.main import create_app
    from fastapi.testclient import TestClient
    from app.core.config import make_settings
    import pytest
    from fastapi import FastAPI
    from app.errors import ConflictError
    app = create_app(make_settings("/tmp-ledger-smoke-err"))
    # 就地注册一个抛错路由验证契约
    app.router.routes  # noqa: 确认已构建
    from fastapi.routing import APIRoute
    def boom(): raise ConflictError("测试冲突")
    app.add_api_route("/api/boom", boom, methods=["GET"])
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/boom")
        assert r.status_code == 409
        assert r.json() == {"code": "conflict", "message": "测试冲突"}
```

- [ ] **Step 4: 运行测试**

Run: `cd backend; python -X utf8 -m pytest tests/test_api_smoke.py -v`
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: 后端骨架（配置/数据库/错误契约/健康检查）"
```

---

### Task 2: 数据模型与 DTO

**Files:**
- Create: `backend/app/models/__init__.py`, `backend/app/models/entities.py`, `backend/app/schemas/__init__.py`, `backend/app/schemas/dtos.py`, `backend/tests/test_models.py`

**Interfaces:**
- Consumes: `Base`（Task 1）
- Produces: ORM 模型 `Project(id,name,customer,contract_no,owner,contract_amount,initial_stage,current_stage,start_date,end_date,note,created_at,updated_at)`、`Node(id,project_id,parent_id,name,stage_key,sort_order,created_at,updated_at)`、`Attachment(id,node_id,original_name,stored_path,size,mime,uploaded_at)`、`PurchaseOrder(id,project_id,name,supplier,amount,order_date,note,created_at)`、`AcceptanceRecord(id,project_id,name,acceptance_date,received_amount,note,created_at)`、`StageHistory(id,project_id,from_stage,to_stage,changed_at)`；Pydantic DTO：`ProjectCreate/ProjectUpdate/StageChange(ProjectOut)`, `NodeOut`, `AttachmentOut`, `Purchase(Create|Update|Out)`, `Acceptance(Create|Update|Out)`, `CaliberItem`, `StatsOut`, `LedgerOut`

- [ ] **Step 1: 写模型往返测试**

`backend/tests/test_models.py`:
```python
from datetime import date
from decimal import Decimal


def test_model_roundtrip(db_session):
    from app.models.entities import (Project, Node, Attachment, PurchaseOrder,
                                     AcceptanceRecord, StageHistory)
    p = Project(name="测试项目", customer="某客户", initial_stage="商机",
                current_stage="商机", contract_amount=Decimal("1000000.00"))
    db_session.add(p); db_session.commit(); db_session.refresh(p)

    anchor = Node(project_id=p.id, parent_id=None, name="商机", stage_key="商机")
    sub = Node(project_id=p.id, parent_id=None, name="子环节", stage_key=None)
    db_session.add_all([anchor, sub]); db_session.commit()

    db_session.add(Attachment(node_id=sub.id, original_name="合同.pdf",
                              stored_path=f"{p.id}/abc.pdf", size=100, mime="application/pdf"))
    db_session.add(PurchaseOrder(project_id=p.id, name="服务器", supplier="华为",
                                 amount=Decimal("1200000.00"), order_date=date(2026, 10, 1)))
    db_session.add(AcceptanceRecord(project_id=p.id, name="初验",
                                    acceptance_date=date(2026, 10, 20),
                                    received_amount=Decimal("300000.00")))
    db_session.add(StageHistory(project_id=p.id, from_stage="商机", to_stage="中标"))
    db_session.commit()

    assert db_session.query(Project).count() == 1
    assert db_session.query(Node).count() == 2
    assert db_session.get(Attachment, 1).original_name == "合同.pdf"
    assert db_session.query(PurchaseOrder).first().amount == Decimal("1200000.00")
    assert db_session.query(AcceptanceRecord).count() == 1
    assert db_session.query(StageHistory).count() == 1

def test_dto_project_out_from_orm(db_session):
    from app.models.entities import Project
    from app.schemas.dtos import ProjectOut
    db_session.add(Project(name="DTO测试", initial_stage="签约", current_stage="签约"))
    db_session.commit()
    p = db_session.query(Project).first()
    out = ProjectOut.model_validate(p)
    assert out.name == "DTO测试"
    assert out.initial_stage == "签约"
```

Run: `python -X utf8 -m pytest tests/test_models.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 2: 实现 entities 与 dtos**

`backend/app/models/entities.py`:
```python
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Column, Date, DateTime, ForeignKey, Integer, Numeric,
                        String, Text)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    customer = Column(String(200), default="")
    contract_no = Column(String(100), default="")
    owner = Column(String(50), default="")
    contract_amount = Column(Numeric(14, 2), default=Decimal("0"))
    initial_stage = Column(String(20), nullable=False)   # 起始阶段（存量起步语义）
    current_stage = Column(String(20), nullable=False)   # 当前阶段（统计/流转口径）
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("nodes.id"), nullable=True)
    name = Column(String(200), nullable=False)
    stage_key = Column(String(20), nullable=True)        # 9 锚点有值=锚点
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Attachment(Base):
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), index=True, nullable=False)
    original_name = Column(String(500), nullable=False)
    stored_path = Column(String(500), nullable=False)    # 相对存储路径 {pid}/{uuid}.ext
    size = Column(Integer, default=0)
    mime = Column(String(100), default="")
    uploaded_at = Column(DateTime, default=datetime.now)


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=False)
    name = Column(String(200), nullable=False)
    supplier = Column(String(200), default="")
    amount = Column(Numeric(14, 2), default=Decimal("0"))   # 元
    order_date = Column(Date, nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class AcceptanceRecord(Base):
    __tablename__ = "acceptance_records"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=False)
    name = Column(String(200), nullable=False)
    acceptance_date = Column(Date, nullable=True)
    received_amount = Column(Numeric(14, 2), default=Decimal("0"))  # 元
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class StageHistory(Base):
    __tablename__ = "stage_histories"
    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=False)
    from_stage = Column(String(20), nullable=False)
    to_stage = Column(String(20), nullable=False)
    changed_at = Column(DateTime, default=datetime.now)
```

`backend/app/schemas/dtos.py`:
```python
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    customer: str = ""
    contract_no: str = ""
    owner: str = ""
    contract_amount: float = 0            # 元
    initial_stage: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    note: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    customer: Optional[str] = None
    contract_no: Optional[str] = None
    owner: Optional[str] = None
    contract_amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    note: Optional[str] = None


class StageChange(BaseModel):
    stage: str


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    customer: str
    contract_no: str
    owner: str
    contract_amount: float
    initial_stage: str
    current_stage: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    note: str
    created_at: datetime
    updated_at: datetime


class NodeOut(BaseModel):
    id: int
    name: str
    stage_key: Optional[str] = None
    is_anchor: bool = False
    attachment_count: int = 0
    children: list["NodeOut"] = []


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    node_id: int
    original_name: str
    stored_path: str
    size: int
    mime: str
    uploaded_at: datetime


class PurchaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    supplier: str = ""
    amount: float = 0                      # 元
    order_date: Optional[date] = None
    note: str = ""


class PurchaseUpdate(BaseModel):
    name: Optional[str] = None
    supplier: Optional[str] = None
    amount: Optional[float] = None
    order_date: Optional[date] = None
    note: Optional[str] = None


class PurchaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    supplier: str
    amount: float
    order_date: Optional[date] = None
    note: str
    created_at: datetime


class AcceptanceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    acceptance_date: Optional[date] = None
    received_amount: float = 0             # 元
    note: str = ""


class AcceptanceUpdate(BaseModel):
    name: Optional[str] = None
    acceptance_date: Optional[date] = None
    received_amount: Optional[float] = None
    note: Optional[str] = None


class AcceptanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    name: str
    acceptance_date: Optional[date] = None
    received_amount: float
    note: str
    created_at: datetime


class CaliberItem(BaseModel):
    count: int
    amount: float                          # 元


class StatsOut(BaseModel):
    forward: CaliberItem
    backward: CaliberItem
    deliver: CaliberItem


class LedgerTotals(BaseModel):
    purchase_amount: float
    received_amount: float


class LedgerOut(BaseModel):
    project: ProjectOut
    tree: list[NodeOut]
    purchases: list[PurchaseOut]
    acceptances: list[AcceptanceOut]
    totals: LedgerTotals
```

两个 `__init__.py` 留空。另外在 `backend/app/core/database.py` 追加导入以触发建表（在 `init_engine` 内）：

```python
# app/core/database.py 的 init_engine 中，create_all 之前加：
import app.models.entities  # noqa: F401 确保模型注册到 Base.metadata
```

- [ ] **Step 3: 运行测试**

Run: `python -X utf8 -m pytest tests/test_models.py -v`
Expected: 2 PASS

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat: 数据模型与Pydantic DTO"
```

---

### Task 3: storage 服务（附件本机存储）

**Files:**
- Create: `backend/app/services/__init__.py`, `backend/app/services/storage.py`, `backend/tests/test_storage.py`

**Interfaces:**
- Consumes: 无
- Produces: `StoredFile(original_name: str, stored_path: str, size: int, mime: str|None)`；`LocalFilesystemStorage(root)`：`.save(fileobj, filename, project_id) -> StoredFile`、`.open_path(stored_path) -> Path`（防路径穿越）、`.remove(stored_path) -> None`（物理缺失容忍）

- [ ] **Step 1: 写失败测试**

`backend/tests/test_storage.py`:
```python
import io


def test_save_returns_uuid_path_keeps_original_name(tmp_path):
    from app.services.storage import LocalFilesystemStorage
    st = LocalFilesystemStorage(tmp_path)
    f = io.BytesIO(b"hello attachment")
    sf = st.save(f, "合同扫描件 v1.pdf", 42)
    assert sf.original_name == "合同扫描件 v1.pdf"
    assert sf.stored_path.startswith("42/")
    assert sf.size == len(b"hello attachment")
    assert not sf.stored_path.endswith("合同扫描件 v1.pdf")   # 物理名是 uuid
    assert (tmp_path / sf.stored_path).exists()

def test_open_path_blocks_traversal(tmp_path):
    from app.services.storage import LocalFilesystemStorage, StorageError
    st = LocalFilesystemStorage(tmp_path)
    st.save(io.BytesIO(b"x"), "a.txt", 1)
    ok = st.open_path("1/a.txt")
    assert ok.exists()
    try:
        st.open_path("../evil.txt")
        raise AssertionError("应当拒绝路径穿越")
    except StorageError:
        pass

def test_remove_tolerates_missing(tmp_path):
    from app.services.storage import LocalFilesystemStorage
    st = LocalFilesystemStorage(tmp_path)
    sf = st.save(io.BytesIO(b"x"), "a.txt", 1)
    st.remove(sf.stored_path)
    assert not (tmp_path / sf.stored_path).exists()
    st.remove(sf.stored_path)      # 再删一次不报错
```

Run: `python -X utf8 -m pytest tests/test_storage.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 2: 实现 storage**

`backend/app/services/storage.py`:
```python
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO


class StorageError(Exception):
    pass


@dataclass
class StoredFile:
    original_name: str
    stored_path: str
    size: int
    mime: str | None


class LocalFilesystemStorage:
    """附件本机存储：{root}/{project_id}/{uuid}{ext}，原名仅记录元数据。"""

    def __init__(self, root: Path):
        self.root = Path(root)

    def save(self, fileobj: BinaryIO, filename: str, project_id: int) -> StoredFile:
        original = Path(filename.replace("\\", "/")).name  # 去路径成分、防注入
        ext = Path(original).suffix[:20]
        rel = f"{project_id}/{uuid.uuid4().hex}{ext}"
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = fileobj.read()
        if isinstance(content, str):
            content = content.encode("utf-8")
        dest.write_bytes(content)
        return StoredFile(original_name=original, stored_path=rel,
                          size=len(content), mime=mimetypes.guess_type(original)[0])

    def open_path(self, stored_path: str) -> Path:
        root = self.root.resolve()
        p = (self.root / stored_path).resolve()
        if root != p and root not in p.parents:
            raise StorageError("非法存储路径")
        return p

    def remove(self, stored_path: str) -> None:
        try:
            self.open_path(stored_path).unlink(missing_ok=True)
        except (StorageError, OSError):
            pass  # 物理缺失容忍：元数据为准
```

- [ ] **Step 3: 运行测试**

Run: `python -X utf8 -m pytest tests/test_storage.py -v`
Expected: 3 PASS

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat: 本机附件存储服务（uuid物理名/防穿越/删除容忍）"
```

---

### Task 4: tree_service（环节树）

**Files:**
- Create: `backend/app/services/tree_service.py`, `backend/tests/test_tree_service.py`

**Interfaces:**
- Consumes: `Node`, `Attachment`, `STAGES`, `NotFoundError`, `ConflictError`, `NodeOut`
- Produces: `create_project_tree(db, project_id)`（建 9 锚点）；`get_tree(db, project_id) -> list[NodeOut]`（含 attachment_count）；`add_node(db, parent_id, name) -> Node`；`rename_node(db, node_id, name)`；`delete_node(db, node_id)`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_tree_service.py`:
```python
import pytest


@pytest.fixture
def project(db_session):
    from app.models.entities import Project
    p = Project(name="树测试", initial_stage="采购", current_stage="采购")
    db_session.add(p); db_session.commit()
    return p


def test_create_tree_nine_anchors(db_session, project):
    from app.services.tree_service import create_project_tree, get_tree
    from app.core.constants import STAGES
    create_project_tree(db_session, project.id)
    tree = get_tree(db_session, project.id)
    assert [t.name for t in tree] == STAGES            # 顺序=生命周期顺序
    assert all(t.is_anchor for t in tree)
    assert all(t.attachment_count == 0 for t in tree)

def test_add_and_nest_node(db_session, project):
    from app.services.tree_service import create_project_tree, add_node, get_tree
    create_project_tree(db_session, project.id)
    anchor = get_tree(db_session, project.id)[4]       # 采购
    sub = add_node(db_session, anchor.id, "硬件采购")
    subsub = add_node(db_session, sub.id, "二标段")
    assert sub.project_id == subsub.project_id == project.id
    tree = get_tree(db_session, project.id)
    buy = tree[4]
    assert buy.children[0].name == "硬件采购"
    assert buy.children[0].children[0].name == "二标段"

def test_rename_anchor_forbidden(db_session, project):
    from app.services.tree_service import create_project_tree, rename_node
    from app.errors import ConflictError
    create_project_tree(db_session, project.id)
    anchors = db_session.query(
        __import__("app.models.entities", fromlist=["Node"]).Node
    ).filter_by(stage_key="采购").one()
    with pytest.raises(ConflictError):
        rename_node(db_session, anchors.id, "改名")

def test_delete_rules(db_session, project):
    from app.models.entities import Node, Attachment
    from app.services.tree_service import create_project_tree, add_node, delete_node
    from app.errors import ConflictError, NotFoundError
    create_project_tree(db_session, project.id)
    anchor = db_session.query(Node).filter_by(stage_key="采购", project_id=project.id).one()
    sub = add_node(db_session, anchor.id, "硬件采购")
    child = add_node(db_session, sub.id, "二标段")

    with pytest.raises(ConflictError):    # 锚点不可删
        delete_node(db_session, anchor.id)
    with pytest.raises(ConflictError):    # 有子环节禁删
        delete_node(db_session, sub.id)
    delete_node(db_session, child.id)     # 清掉子环节
    db_session.add(Attachment(node_id=sub.id, original_name="x.pdf",
                              stored_path="1/x.pdf", size=1))
    db_session.commit()
    with pytest.raises(ConflictError):    # 有附件禁删
        delete_node(db_session, sub.id)
    db_session.query(Attachment).filter_by(node_id=sub.id).delete()
    db_session.commit()
    delete_node(db_session, sub.id)       # 清空后可删
    with pytest.raises(NotFoundError):    # 不存在的节点
        delete_node(db_session, 99999)

def test_add_node_cross_project_blocked(db_session, project):
    from app.models.entities import Project
    from app.services.tree_service import create_project_tree, add_node
    from app.errors import NotFoundError
    p2 = Project(name="另一项目", initial_stage="商机", current_stage="商机")
    db_session.add(p2); db_session.commit()
    create_project_tree(db_session, project.id)
    anchor = db_session.query(
        __import__("app.models.entities", fromlist=["Node"]).Node
    ).filter_by(stage_key="采购", project_id=project.id).one()
    # parent_id 不存在（另一项目的节点 id 不传）
    with pytest.raises(NotFoundError):
        add_node(db_session, 99999, "无父")
```

Run: `python -X utf8 -m pytest tests/test_tree_service.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 2: 实现 tree_service**

`backend/app/services/tree_service.py`:
```python
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import STAGES
from app.errors import ConflictError, NotFoundError
from app.models.entities import Attachment, Node
from app.schemas.dtos import NodeOut


def create_project_tree(db: Session, project_id: int) -> None:
    """项目创建时调用：生成 9 个阶段锚点。"""
    for i, stage in enumerate(STAGES):
        db.add(Node(project_id=project_id, parent_id=None,
                    name=stage, stage_key=stage, sort_order=i))
    db.commit()


def get_tree(db: Session, project_id: int) -> list[NodeOut]:
    nodes = (db.query(Node).filter(Node.project_id == project_id)
             .order_by(Node.sort_order, Node.id).all())
    counts = dict(db.query(Attachment.node_id, func.count(Attachment.id))
                  .group_by(Attachment.node_id).all())
    by_parent: dict[int | None, list[Node]] = defaultdict(list)
    for n in nodes:
        by_parent[n.parent_id].append(n)

    def build(n: Node) -> NodeOut:
        return NodeOut(id=n.id, name=n.name, stage_key=n.stage_key,
                       is_anchor=n.stage_key is not None,
                       attachment_count=counts.get(n.id, 0),
                       children=[build(c) for c in by_parent[n.id]])

    return [build(n) for n in by_parent[None]]


def _get_node(db: Session, node_id: int) -> Node:
    node = db.get(Node, node_id)
    if node is None:
        raise NotFoundError("环节不存在")
    return node


def add_node(db: Session, parent_id: int, name: str) -> Node:
    parent = db.get(Node, parent_id)
    if parent is None:
        raise NotFoundError("父环节不存在")
    node = Node(project_id=parent.project_id, parent_id=parent.id,
                name=name, stage_key=None, sort_order=0)
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


def rename_node(db: Session, node_id: int, name: str) -> None:
    node = _get_node(db, node_id)
    if node.stage_key is not None:
        raise ConflictError("阶段锚点不可改名")
    node.name = name
    db.commit()


def delete_node(db: Session, node_id: int) -> None:
    node = _get_node(db, node_id)
    if node.stage_key is not None:
        raise ConflictError("阶段锚点不可删除（账本骨架）")
    if db.query(Node).filter(Node.parent_id == node_id).count():
        raise ConflictError("该环节下有子环节，请先清空子环节")
    if db.query(Attachment).filter(Attachment.node_id == node_id).count():
        raise ConflictError("该环节挂有附件，请先删除附件")
    db.delete(node)
    db.commit()
```

- [ ] **Step 3: 运行测试**

Run: `python -X utf8 -m pytest tests/test_tree_service.py -v`
Expected: 5 PASS

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat: 环节树服务（9锚点/递归树/锚点与非空删除保护）"
```

---

### Task 5: project_service（项目+阶段流转+一账聚合）

**Files:**
- Create: `backend/app/services/project_service.py`, `backend/tests/test_project_service.py`

**Interfaces:**
- Consumes: `tree_service.*`、`Project`、`StageHistory`、`PurchaseOrder`、`AcceptanceRecord`、`STAGES`、错误家族、DTO
- Produces: `create_project(db, data: ProjectCreate) -> Project`（自动建锚点树）；`search_projects(db, keyword="", stage=None) -> list[Project]`；`update_project(db, project_id, data: ProjectUpdate) -> Project`；`change_stage(db, project_id, target_stage: str) -> Project`（写 StageHistory，允许跳转/回退）；`get_ledger(db, project_id) -> LedgerOut`（含 totals）

- [ ] **Step 1: 写失败测试**

`backend/tests/test_project_service.py`:
```python
import pytest
from app.schemas.dtos import ProjectCreate, ProjectUpdate


def test_create_from_any_stage_with_anchors(db_session):
    from app.services import project_service as ps
    p = ps.create_project(db_session, ProjectCreate(
        name="存量项目", customer="某局", initial_stage="采购",
        contract_amount=8600000))
    assert p.current_stage == p.initial_stage == "采购"
    from app.models.entities import Node
    assert db_session.query(Node).filter_by(project_id=p.id).count() == 9

def test_create_invalid_stage(db_session):
    from app.services import project_service as ps
    from app.errors import InvalidError
    with pytest.raises(InvalidError):
        ps.create_project(db_session, ProjectCreate(name="x", initial_stage="神秘阶段"))

def test_search(db_session):
    from app.services import project_service as ps
    ps.create_project(db_session, ProjectCreate(name="政务云灾备", initial_stage="商机"))
    ps.create_project(db_session, ProjectCreate(name="卫健大模型", initial_stage="商机"))
    ps.create_project(db_session, ProjectCreate(name="园区一期", initial_stage="采购"))
    [p] = ps.search_projects(db_session, keyword="卫健")
    assert p.name == "卫健大模型"
    assert len(ps.search_projects(db_session, stage="采购")) == 1
    assert len(ps.search_projects(db_session)) == 3

def test_change_stage_matrix(db_session):
    from app.services import project_service as ps
    from app.models.entities import StageHistory
    from app.errors import InvalidError
    p = ps.create_project(db_session, ProjectCreate(name="流转", initial_stage="商机"))
    p = ps.change_stage(db_session, p.id, "签约")     # 跳转
    assert p.current_stage == "签约"
    p = ps.change_stage(db_session, p.id, "立项")     # 推进
    p = ps.change_stage(db_session, p.id, "商机")     # 回退
    assert p.current_stage == "商机"
    hist = db_session.query(StageHistory).filter_by(project_id=p.id).all()
    assert [(h.from_stage, h.to_stage) for h in hist] == \
        [("商机", "签约"), ("签约", "立项"), ("立项", "商机")]
    with pytest.raises(InvalidError):
        ps.change_stage(db_session, p.id, "不存在阶段")

def test_get_ledger_complete(db_session):
    from app.services import project_service as ps
    from app.schemas.dtos import PurchaseCreate, AcceptanceCreate
    from app.services.detail_service import create_purchase, create_acceptance
    from app.services.tree_service import get_tree, add_node
    p = ps.create_project(db_session, ProjectCreate(
        name="一账", initial_stage="采购", contract_amount=1000000))
    create_purchase(db_session, p.id, PurchaseCreate(name="防火墙", amount=1200000))
    create_purchase(db_session, p.id, PurchaseCreate(name="交换机", amount=800000))
    create_acceptance(db_session, p.id, AcceptanceCreate(name="初验", received_amount=300000))

    ledger = ps.get_ledger(db_session, p.id)
    assert ledger.project.id == p.id
    assert [t.name for t in ledger.tree][0] == "商机"
    assert len(ledger.purchases) == 2
    assert float(ledger.totals.purchase_amount) == 2000000
    assert float(ledger.totals.received_amount) == 300000
```

Run: `python -X utf8 -m pytest tests/test_project_service.py -v`
Expected: FAIL（detail_service 未实现，属预期：先写完本任务实现使其通过）

- [ ] **Step 2: 实现 project_service**

`backend/app/services/project_service.py`:
```python
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import STAGES
from app.errors import InvalidError, NotFoundError
from app.models.entities import AcceptanceRecord, Project, PurchaseOrder, StageHistory
from app.schemas.dtos import (LedgerOut, LedgerTotals, ProjectCreate,
                              ProjectOut, ProjectUpdate)
from app.services import tree_service


def _get_project(db: Session, project_id: int) -> Project:
    p = db.get(Project, project_id)
    if p is None:
        raise NotFoundError("项目不存在")
    return p


def create_project(db: Session, data: ProjectCreate) -> Project:
    if data.initial_stage not in STAGES:
        raise InvalidError("起始阶段非法，必须是 9 个阶段之一")
    p = Project(name=data.name, customer=data.customer,
                contract_no=data.contract_no, owner=data.owner,
                contract_amount=Decimal(str(data.contract_amount)),
                initial_stage=data.initial_stage, current_stage=data.initial_stage,
                start_date=data.start_date, end_date=data.end_date, note=data.note)
    db.add(p)
    db.commit()
    db.refresh(p)
    tree_service.create_project_tree(db, p.id)   # 自动生成 9 锚点
    return p


def search_projects(db: Session, keyword: str = "", stage: str | None = None) -> list[Project]:
    q = db.query(Project)
    if keyword:
        q = q.filter(Project.name.contains(keyword))
    if stage:
        q = q.filter(Project.current_stage == stage)
    return q.order_by(Project.id.desc()).all()


def update_project(db: Session, project_id: int, data: ProjectUpdate) -> Project:
    p = _get_project(db, project_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "contract_amount":
            value = Decimal(str(value))
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


def change_stage(db: Session, project_id: int, target_stage: str) -> Project:
    p = _get_project(db, project_id)
    if target_stage not in STAGES:
        raise InvalidError("目标阶段非法，必须是 9 个阶段之一")
    if target_stage != p.current_stage:
        db.add(StageHistory(project_id=p.id, from_stage=p.current_stage,
                            to_stage=target_stage))
        p.current_stage = target_stage
        db.commit()
        db.refresh(p)
    return p


def get_ledger(db: Session, project_id: int) -> LedgerOut:
    p = _get_project(db, project_id)
    tree = tree_service.get_tree(db, project_id)
    purchases = (db.query(PurchaseOrder).filter_by(project_id=project_id)
                 .order_by(PurchaseOrder.id).all())
    acceptances = (db.query(AcceptanceRecord).filter_by(project_id=project_id)
                   .order_by(AcceptanceRecord.id).all())
    purchase_sum = db.query(func.coalesce(func.sum(PurchaseOrder.amount), 0)) \
        .filter_by(project_id=project_id).scalar()
    received_sum = db.query(func.coalesce(func.sum(AcceptanceRecord.received_amount), 0)) \
        .filter_by(project_id=project_id).scalar()
    return LedgerOut(
        project=ProjectOut.model_validate(p),
        tree=tree,
        purchases=[type("P", (), {}) and __import__("app.schemas.dtos", fromlist=["PurchaseOut"]).PurchaseOut.model_validate(x) for x in purchases],
        acceptances=[__import__("app.schemas.dtos", fromlist=["AcceptanceOut"]).AcceptanceOut.model_validate(x) for x in acceptances],
        totals=LedgerTotals(purchase_amount=float(purchase_sum),
                            received_amount=float(received_sum)))
```

> 注：`get_ledger` 中动态 import 为笔误防护——实际编码时直接 `from app.schemas.dtos import PurchaseOut, AcceptanceOut` 顶部导入并使用 `PurchaseOut.model_validate(x)`，与 tree 同风格。（计划层面以顶部导入为准。）

- [ ] **Step 3: 先实现 detail_service 最小版（Task 6 依赖）**

见 Task 6——若按顺序执行，此处先创建 `detail_service.py` 的 `create_purchase/create_acceptance`（Task 6 完整实现），使本任务测试可运行。

- [ ] **Step 4: 运行测试**

Run: `python -X utf8 -m pytest tests/test_project_service.py -v`
Expected: 5 PASS

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: 项目服务（任意阶段创建/检索/流转矩阵/一账聚合）"
```

---

### Task 6: detail_service（采购/验收明细）

**Files:**
- Create: `backend/app/services/detail_service.py`, `backend/tests/test_detail_service.py`

**Interfaces:**
- Consumes: `Project`、`PurchaseOrder`、`AcceptanceRecord`、错误家族、DTO
- Produces: 采购：`list_purchases(db, project_id) / create_purchase(db, project_id, data: PurchaseCreate) / update_purchase(db, id, data: PurchaseUpdate) / delete_purchase(db, id)`；验收：`list_acceptances / create_acceptance(db, project_id, data: AcceptanceCreate) / update_acceptance / delete_acceptance`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_detail_service.py`:
```python
import pytest
from app.schemas.dtos import PurchaseCreate, AcceptanceCreate


@pytest.fixture
def project(db_session):
    from app.models.entities import Project
    p = Project(name="明细测试", initial_stage="采购", current_stage="采购")
    db_session.add(p); db_session.commit()
    return p


def test_purchase_crud_and_sum(db_session, project):
    from app.services import detail_service as ds
    ds.create_purchase(db_session, project.id, PurchaseCreate(name="防火墙", supplier="华为", amount=1200000))
    ds.create_purchase(db_session, project.id, PurchaseCreate(name="交换机", supplier="新华三", amount=800000))
    rows = ds.list_purchases(db_session, project.id)
    assert len(rows) == 2
    assert sum(r.amount for r in rows) == 2000000
    ds.delete_purchase(db_session, rows[0].id)
    assert len(ds.list_purchases(db_session, project.id)) == 1

def test_acceptance_crud_and_sum(db_session, project):
    from app.services import detail_service as ds
    from app.schemas.dtos import PurchaseUpdate, AcceptanceUpdate
    ds.create_acceptance(db_session, project.id, AcceptanceCreate(name="初验", received_amount=300000))
    rows = ds.list_acceptances(db_session, project.id)
    assert float(rows[0].received_amount) == 300000
    ds.update_acceptance(db_session, rows[0].id, AcceptanceUpdate(received_amount=350000))
    assert float(ds.list_acceptances(db_session, project.id)[0].received_amount) == 350000
    ds.delete_acceptance(db_session, rows[0].id)
    assert ds.list_acceptances(db_session, project.id) == []

def test_negative_amount_rejected(db_session, project):
    from app.services import detail_service as ds
    from app.errors import InvalidError
    with pytest.raises(InvalidError):
        ds.create_purchase(db_session, project.id, PurchaseCreate(name="x", amount=-1))
    with pytest.raises(InvalidError):
        ds.create_acceptance(db_session, project.id, AcceptanceCreate(name="y", received_amount=-5))

def test_project_must_exist(db_session):
    from app.services import detail_service as ds
    from app.errors import NotFoundError
    with pytest.raises(NotFoundError):
        ds.create_purchase(db_session, 99999, PurchaseCreate(name="x"))
    with pytest.raises(NotFoundError):
        ds.list_acceptances(db_session, 99999)
```

Run: `python -X utf8 -m pytest tests/test_detail_service.py -v`
Expected: FAIL 前 Service 未建

- [ ] **Step 2: 实现 detail_service**

`backend/app/services/detail_service.py`:
```python
from decimal import Decimal

from sqlalchemy.orm import Session

from app.errors import InvalidError, NotFoundError
from app.models.entities import AcceptanceRecord, Project, PurchaseOrder
from app.schemas.dtos import (AcceptanceCreate, AcceptanceUpdate,
                              PurchaseCreate, PurchaseUpdate)


def _ensure_project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("项目不存在")


# ---------- 采购 ----------
def list_purchases(db: Session, project_id: int) -> list[PurchaseOrder]:
    _ensure_project(db, project_id)
    return (db.query(PurchaseOrder).filter_by(project_id=project_id)
            .order_by(PurchaseOrder.id).all())


def create_purchase(db: Session, project_id: int, data: PurchaseCreate) -> PurchaseOrder:
    _ensure_project(db, project_id)
    if data.amount < 0:
        raise InvalidError("采购金额不能为负")
    row = PurchaseOrder(project_id=project_id, name=data.name,
                        supplier=data.supplier,
                        amount=Decimal(str(data.amount)),
                        order_date=data.order_date, note=data.note)
    db.add(row); db.commit(); db.refresh(row)
    return row


def update_purchase(db: Session, purchase_id: int, data: PurchaseUpdate) -> PurchaseOrder:
    row = db.get(PurchaseOrder, purchase_id)
    if row is None:
        raise NotFoundError("采购单不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "amount":
            if value < 0:
                raise InvalidError("采购金额不能为负")
            value = Decimal(str(value))
        setattr(row, field, value)
    db.commit(); db.refresh(row)
    return row


def delete_purchase(db: Session, purchase_id: int) -> None:
    row = db.get(PurchaseOrder, purchase_id)
    if row is None:
        raise NotFoundError("采购单不存在")
    db.delete(row); db.commit()


# ---------- 验收 ----------
def list_acceptances(db: Session, project_id: int) -> list[AcceptanceRecord]:
    _ensure_project(db, project_id)
    return (db.query(AcceptanceRecord).filter_by(project_id=project_id)
            .order_by(AcceptanceRecord.id).all())


def create_acceptance(db: Session, project_id: int, data: AcceptanceCreate) -> AcceptanceRecord:
    _ensure_project(db, project_id)
    if data.received_amount < 0:
        raise InvalidError("回款金额不能为负")
    row = AcceptanceRecord(project_id=project_id, name=data.name,
                           acceptance_date=data.acceptance_date,
                           received_amount=Decimal(str(data.received_amount)),
                           note=data.note)
    db.add(row); db.commit(); db.refresh(row)
    return row


def update_acceptance(db: Session, acceptance_id: int, data: AcceptanceUpdate) -> AcceptanceRecord:
    row = db.get(AcceptanceRecord, acceptance_id)
    if row is None:
        raise NotFoundError("验收记录不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "received_amount":
            if value < 0:
                raise InvalidError("回款金额不能为负")
            value = Decimal(str(value))
        setattr(row, field, value)
    db.commit(); db.refresh(row)
    return row


def delete_acceptance(db: Session, acceptance_id: int) -> None:
    row = db.get(AcceptanceRecord, acceptance_id)
    if row is None:
        raise NotFoundError("验收记录不存在")
    db.delete(row); db.commit()
```

- [ ] **Step 3: 运行测试（连同 Task 5 一起）**

Run: `python -X utf8 -m pytest tests/test_detail_service.py tests/test_project_service.py -v`
Expected: 全部 PASS

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat: 采购/验收明细服务（CRUD+非负校验+项目存在校验）"
```

---

### Task 7: stats_service（三口径 + Excel 导出）

**Files:**
- Create: `backend/app/services/stats_service.py`, `backend/tests/test_stats_service.py`

**Interfaces:**
- Consumes: `Project`、`PurchaseOrder`、`AcceptanceRecord`、`StatsOut`
- Produces: `calibers(db) -> StatsOut`（前向=有签约额项目数与 Σ；后向=有采购单项目数与 Σ；交付=有验收回款项目数与 Σ）；`export_xlsx(db) -> bytes`（3 sheet：前向签约明细/后向采购明细/交付回款明细）

- [ ] **Step 1: 写失败测试**

`backend/tests/test_stats_service.py`:
```python
from io import BytesIO

from app.schemas.dtos import (AcceptanceCreate, ProjectCreate, PurchaseCreate)
from app.services import project_service as ps
from app.services import detail_service as ds


def seed(db_session):
    p1 = ps.create_project(db_session, ProjectCreate(name="甲", initial_stage="采购", contract_amount=8600000))
    p2 = ps.create_project(db_session, ProjectCreate(name="乙", initial_stage="商机", contract_amount=0))
    ps.create_project(db_session, ProjectCreate(name="丙", initial_stage="实施", contract_amount=5000000))
    ds.create_purchase(db_session, p1.id, PurchaseCreate(name="a", amount=1200000))
    ds.create_purchase(db_session, p1.id, PurchaseCreate(name="b", amount=800000))
    ds.create_acceptance(db_session, p1.id, AcceptanceCreate(name="初验", received_amount=300000))
    return p1, p2


def test_calibers(db_session):
    from app.services.stats_service import calibers
    seed(db_session)
    s = calibers(db_session)
    assert (s.forward.count, s.forward.amount) == (2, 13600000)     # 甲+丙有签约额
    assert (s.backward.count, s.backward.amount) == (1, 2000000)
    assert (s.deliver.count, s.deliver.amount) == (1, 300000)

def test_calibers_empty(db_session):
    from app.services.stats_service import calibers
    s = calibers(db_session)
    assert (s.forward.count, s.forward.amount) == (0, 0)
    assert (s.backward.count, s.backward.amount) == (0, 0)
    assert (s.deliver.count, s.deliver.amount) == (0, 0)

def test_export_xlsx_openable(db_session):
    from openpyxl import load_workbook
    from app.services.stats_service import export_xlsx
    seed(db_session)
    content = export_xlsx(db_session)
    wb = load_workbook(BytesIO(content))
    assert wb.sheetnames == ["前向-签约明细", "后向-采购明细", "交付-回款明细"]
    ws = wb["后向-采购明细"]
    assert ws.max_row >= 3     # 表头 + 2 笔明细
    assert ws.cell(1, 1).value == "项目名称"
```

Run: `python -X utf8 -m pytest tests/test_stats_service.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 2: 实现 stats_service**

`backend/app/services/stats_service.py`:
```python
from io import BytesIO

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.entities import AcceptanceRecord, Project, PurchaseOrder
from app.schemas.dtos import CaliberItem, StatsOut


def calibers(db: Session) -> StatsOut:
    fwd_count = db.query(func.count(Project.id)) \
        .filter(Project.contract_amount > 0).scalar()
    fwd_amount = db.query(func.coalesce(func.sum(Project.contract_amount), 0)) \
        .filter(Project.contract_amount > 0).scalar()

    back = db.query(func.count(func.distinct(PurchaseOrder.project_id)),
                    func.coalesce(func.sum(PurchaseOrder.amount), 0)).one()
    deliv = db.query(func.count(func.distinct(AcceptanceRecord.project_id)),
                     func.coalesce(func.sum(AcceptanceRecord.received_amount), 0)).one()
    return StatsOut(
        forward=CaliberItem(count=int(fwd_count), amount=float(fwd_amount)),
        backward=CaliberItem(count=int(back[0]), amount=float(back[1])),
        deliver=CaliberItem(count=int(deliv[0]), amount=float(deliv[1])))


def export_xlsx(db: Session) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "前向-签约明细"
    ws1.append(["项目名称", "客户", "合同编号", "当前阶段", "签约金额(元)", "负责人", "起始日期", "结束日期"])
    for p in db.query(Project).order_by(Project.id).all():
        ws1.append([p.name, p.customer, p.contract_no, p.current_stage,
                    float(p.contract_amount or 0), p.owner,
                    str(p.start_date or ""), str(p.end_date or "")])

    ws2 = wb.create_sheet("后向-采购明细")
    ws2.append(["项目名称", "采购名称", "供应商", "采购金额(元)", "采购日期", "备注"])
    for r in db.query(PurchaseOrder).order_by(PurchaseOrder.id).all():
        project = db.get(Project, r.project_id)
        ws2.append([project.name if project else "", r.name, r.supplier,
                    float(r.amount or 0), str(r.order_date or ""), r.note])

    ws3 = wb.create_sheet("交付-回款明细")
    ws3.append(["项目名称", "验收名称", "回款金额(元)", "验收日期", "备注"])
    for r in db.query(AcceptanceRecord).order_by(AcceptanceRecord.id).all():
        project = db.get(Project, r.project_id)
        ws3.append([project.name if project else "", r.name,
                    float(r.received_amount or 0), str(r.acceptance_date or ""), r.note])

    bio = BytesIO()
    wb.save(bio)
    return bio.getvalue()
```

- [ ] **Step 3: 运行测试**

Run: `python -X utf8 -m pytest tests/test_stats_service.py -v`
Expected: 3 PASS

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "feat: 三口径统计与Excel导出（3 sheet明细）"
```

---

### Task 8: API 路由层 + 全链路集成测试

**Files:**
- Create: `backend/app/api/__init__.py`, `backend/app/api/deps.py`, `backend/app/api/projects.py`, `backend/app/api/nodes.py`, `backend/app/api/attachments.py`, `backend/app/api/purchases.py`, `backend/app/api/acceptances.py`, `backend/app/api/stats.py`
- Modify: `backend/app/main.py`（注册路由）
- Test: `backend/tests/test_api_smoke.py`（追加全链路用例）

**Interfaces:**
- Consumes: 全部 services、DTO、错误家族、`LocalFilesystemStorage`
- Produces: REST 端点（见下）；`get_storage` 依赖（`request.app.state.storage`）

路由清单（架构设计 §4）：
```
POST   /api/projects                        201
GET    /api/projects?keyword=&stage=        200
PUT    /api/projects/{id}                   200
PATCH  /api/projects/{id}/stage             200
GET    /api/projects/{id}/ledger            200
POST   /api/nodes                           201 {parent_id, name}
PATCH  /api/nodes/{id}                      200 {name}
DELETE /api/nodes/{id}                      204（非空 409）
POST   /api/nodes/{id}/attachments          201 multipart(file)
GET    /api/nodes/{id}/attachments          200
GET    /api/attachments/{id}/download       200 FileResponse
DELETE /api/attachments/{id}                204
GET/POST /api/projects/{pid}/purchases      200/201
PUT/DELETE /api/purchases/{id}              200/204
GET/POST /api/projects/{pid}/acceptances    200/201
PUT/DELETE /api/acceptances/{id}            200/204
GET    /api/stats                           200
GET    /api/stats/export                    200 xlsx 流
```

- [ ] **Step 1: 写全链路失败测试（追加到 test_api_smoke.py）**

```python
# backend/tests/test_api_smoke.py 追加
def test_full_chain(client):
    """建项目→锚点→子环节→附件→采购验证→统计→导出 一条链跑通。"""
    from io import BytesIO
    from openpyxl import load_workbook

    # 1) 建项目（存量从采购起步）
    r = client.post("/api/projects", json={
        "name": "政务云灾备扩容", "customer": "省政务服务中心",
        "initial_stage": "采购", "contract_amount": 8600000})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    # 2) 一账详情：9 锚点
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert len(ledger["tree"]) == 9
    assert ledger["project"]["current_stage"] == "采购"

    # 3) 阶段流转 + 非法阶段
    assert client.patch(f"/api/projects/{pid}/stage",
                        json={"stage": "实施"}).status_code == 200
    assert client.patch(f"/api/projects/{pid}/stage",
                        json={"stage": "不存在"}).status_code == 422

    # 4) 子环节 + 嵌套
    anchor_id = ledger["tree"][4]["id"]            # 采购锚点
    r = client.post("/api/nodes", json={"parent_id": anchor_id, "name": "硬件采购"})
    assert r.status_code == 201
    sub_id = r.json()["id"]
    assert client.post("/api/nodes", json={"parent_id": sub_id, "name": "二标段"}).status_code == 201

    # 5) 附件上传/下载/列表/删除
    r = client.post(f"/api/nodes/{sub_id}/attachments",
                    files={"file": ("验收报告.pdf", BytesIO(b"%PDF-fake"), "application/pdf")})
    assert r.status_code == 201, r.text
    att = r.json()
    assert att["original_name"] == "验收报告.pdf"
    dl = client.get(f"/api/attachments/{att['id']}/download")
    assert dl.status_code == 200 and dl.content == b"%PDF-fake"
    assert len(client.get(f"/api/nodes/{sub_id}/attachments").json()) == 1
    assert client.delete(f"/api/attachments/{att['id']}").status_code == 204

    # 6) 非空节点删除保护（子环节下还有"二标段"）
    r = client.delete(f"/api/nodes/{sub_id}")
    assert r.status_code == 409
    assert r.json() == {"code": "conflict", "message": "该环节下有子环节，请先清空子环节"}

    # 7) 采购/验收明细
    assert client.post(f"/api/projects/{pid}/purchases",
                       json={"name": "防火墙", "supplier": "华为", "amount": 1200000}).status_code == 201
    assert client.post(f"/api/projects/{pid}/acceptances",
                       json={"name": "初验", "received_amount": 300000}).status_code == 201
    ledger = client.get(f"/api/projects/{pid}/ledger").json()
    assert float(ledger["totals"]["purchase_amount"]) == 1200000
    assert float(ledger["totals"]["received_amount"]) == 300000

    # 8) 检索
    assert len(client.get("/api/projects", params={"keyword": "灾备"}).json()) == 1
    assert len(client.get("/api/projects", params={"stage": "实施"}).json()) == 1

    # 9) 统计 + 导出可打开
    stats = client.get("/api/stats").json()
    assert stats["forward"]["amount"] == 8600000
    assert stats["backward"]["amount"] == 1200000
    exp = client.get("/api/stats/export")
    assert exp.status_code == 200
    wb = load_workbook(BytesIO(exp.content))
    assert wb.sheetnames == ["前向-签约明细", "后向-采购明细", "交付-回款明细"]

def test_404_contract(client):
    assert client.get("/api/projects/999/ledger").status_code == 404
    assert client.get("/api/projects/999/ledger").json()["code"] == "not_found"
```

Run: `python -X utf8 -m pytest tests/test_api_smoke.py -v`
Expected: 新用例 FAIL（404 路由不存在）

- [ ] **Step 2: 实现路由层**

`backend/app/api/deps.py`:
```python
from fastapi import Request

from app.services.storage import LocalFilesystemStorage


def get_storage(request: Request) -> LocalFilesystemStorage:
    return request.app.state.storage
```

`backend/app/api/projects.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import ProjectCreate, ProjectOut, ProjectUpdate, StageChange
from app.services import project_service as ps

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", status_code=201, response_model=ProjectOut)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    return ps.create_project(db, data)


@router.get("", response_model=list[ProjectOut])
def list_projects(keyword: str = "", stage: str | None = None,
                  db: Session = Depends(get_db)):
    return ps.search_projects(db, keyword, stage)


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, data: ProjectUpdate,
                   db: Session = Depends(get_db)):
    return ps.update_project(db, project_id, data)


@router.patch("/{project_id}/stage", response_model=ProjectOut)
def change_stage(project_id: int, data: StageChange,
                 db: Session = Depends(get_db)):
    return ps.change_stage(db, project_id, data.stage)


@router.get("/{project_id}/ledger")
def get_ledger(project_id: int, db: Session = Depends(get_db)):
    return ps.get_ledger(db, project_id)
```

`backend/app/api/nodes.py`:
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import tree_service as ts

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


class NodeCreate(BaseModel):
    parent_id: int
    name: str


class NodeRename(BaseModel):
    name: str


@router.post("", status_code=201)
def add_node(data: NodeCreate, db: Session = Depends(get_db)):
    node = ts.add_node(db, data.parent_id, data.name)
    return {"id": node.id, "parent_id": node.parent_id, "name": node.name,
            "project_id": node.project_id}


@router.patch("/{node_id}")
def rename_node(node_id: int, data: NodeRename, db: Session = Depends(get_db)):
    ts.rename_node(db, node_id, data.name)
    return {"ok": True}


@router.delete("/{node_id}", status_code=204)
def delete_node(node_id: int, db: Session = Depends(get_db)):
    ts.delete_node(db, node_id)
    return None
```

`backend/app/api/attachments.py`:
```python
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.errors import NotFoundError
from app.models.entities import Attachment, Node
from app.schemas.dtos import AttachmentOut
from app.api.deps import get_storage

router = APIRouter(tags=["attachments"])


@router.post("/api/nodes/{node_id}/attachments", status_code=201,
             response_model=AttachmentOut)
def upload_attachment(node_id: int, file: UploadFile = File(...),
                      db: Session = Depends(get_db),
                      storage=Depends(get_storage)):
    node = db.get(Node, node_id)
    if node is None:
        raise NotFoundError("环节不存在")
    stored = storage.save(file.file, file.filename or "unnamed", node.project_id)
    att = Attachment(node_id=node_id, original_name=stored.original_name,
                     stored_path=stored.stored_path, size=stored.size,
                     mime=stored.mime or "")
    db.add(att)          # 先存文件成功，再写库（不留孤儿记录）
    db.commit()
    db.refresh(att)
    return att


@router.get("/api/nodes/{node_id}/attachments", response_model=list[AttachmentOut])
def list_attachments(node_id: int, db: Session = Depends(get_db)):
    if db.get(Node, node_id) is None:
        raise NotFoundError("环节不存在")
    return db.query(Attachment).filter_by(node_id=node_id) \
        .order_by(Attachment.id).all()


@router.get("/api/attachments/{att_id}/download")
def download_attachment(att_id: int, db: Session = Depends(get_db),
                        storage=Depends(get_storage)):
    att = db.get(Attachment, att_id)
    if att is None:
        raise NotFoundError("附件不存在")
    return FileResponse(storage.open_path(att.stored_path),
                        filename=att.original_name)


@router.delete("/api/attachments/{att_id}", status_code=204)
def delete_attachment(att_id: int, db: Session = Depends(get_db),
                      storage=Depends(get_storage)):
    att = db.get(Attachment, att_id)
    if att is None:
        raise NotFoundError("附件不存在")
    db.delete(att)
    db.commit()
    storage.remove(att.stored_path)   # 先删记录再删文件，物理缺失容忍
    return None
```

`backend/app/api/purchases.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import PurchaseCreate, PurchaseOut, PurchaseUpdate
from app.services import detail_service as ds

router = APIRouter(tags=["purchases"])


@router.get("/api/projects/{project_id}/purchases", response_model=list[PurchaseOut])
def list_purchases(project_id: int, db: Session = Depends(get_db)):
    return ds.list_purchases(db, project_id)


@router.post("/api/projects/{project_id}/purchases", status_code=201,
             response_model=PurchaseOut)
def create_purchase(project_id: int, data: PurchaseCreate,
                    db: Session = Depends(get_db)):
    return ds.create_purchase(db, project_id, data)


@router.put("/api/purchases/{purchase_id}", response_model=PurchaseOut)
def update_purchase(purchase_id: int, data: PurchaseUpdate,
                    db: Session = Depends(get_db)):
    return ds.update_purchase(db, purchase_id, data)


@router.delete("/api/purchases/{purchase_id}", status_code=204)
def delete_purchase(purchase_id: int, db: Session = Depends(get_db)):
    ds.delete_purchase(db, purchase_id)
    return None
```

`backend/app/api/acceptances.py`:
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import (AcceptanceCreate, AcceptanceOut, AcceptanceUpdate)
from app.services import detail_service as ds

router = APIRouter(tags=["acceptances"])


@router.get("/api/projects/{project_id}/acceptances", response_model=list[AcceptanceOut])
def list_acceptances(project_id: int, db: Session = Depends(get_db)):
    return ds.list_acceptances(db, project_id)


@router.post("/api/projects/{project_id}/acceptances", status_code=201,
             response_model=AcceptanceOut)
def create_acceptance(project_id: int, data: AcceptanceCreate,
                      db: Session = Depends(get_db)):
    return ds.create_acceptance(db, project_id, data)


@router.put("/api/acceptances/{acceptance_id}", response_model=AcceptanceOut)
def update_acceptance(acceptance_id: int, data: AcceptanceUpdate,
                      db: Session = Depends(get_db)):
    return ds.update_acceptance(db, acceptance_id, data)


@router.delete("/api/acceptances/{acceptance_id}", status_code=204)
def delete_acceptance(acceptance_id: int, db: Session = Depends(get_db)):
    ds.delete_acceptance(db, acceptance_id)
    return None
```

`backend/app/api/stats.py`:
```python
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import StatsOut
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    return stats_service.calibers(db)


@router.get("/export")
def export(db: Session = Depends(get_db)):
    content = stats_service.export_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=ledger-report.xlsx"})
```

`backend/app/main.py` 修改：在异常处理器之后追加路由注册：
```python
    from app.api import acceptances, attachments, nodes, projects, purchases, stats
    app.include_router(projects.router)
    app.include_router(nodes.router)
    app.include_router(attachments.router)
    app.include_router(purchases.router)
    app.include_router(acceptances.router)
    app.include_router(stats.router)
```

- [ ] **Step 3: 运行全量测试**

Run: `python -X utf8 -m pytest tests -v`
Expected: 全部 PASS（models/storage/tree/project/detail/stats/smoke）

- [ ] **Step 4: 启动服务目检 OpenAPI**

Run（手动验证一次）: `cd backend; python -X utf8 -m uvicorn app.main:app --port 8000`
浏览器打开 `http://127.0.0.1:8000/docs` 确认路由齐全后 Ctrl+C。

- [ ] **Step 5: Commit**

```bash
git add backend
git commit -m "feat: API路由层与全链路集成测试（一账流程贯通）"
```

---

### Task 9: 前端骨架（Vite+Vue3+ElementPlus+API 封装）

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.js`, `frontend/index.html`, `frontend/src/main.js`, `frontend/src/App.vue`, `frontend/src/router.js`, `frontend/src/api/index.js`

**Interfaces:**
- Consumes: Task 8 的 REST API
- Produces: `http`（axios 实例，错误 toast 统一）；`projectsApi/{list,create,update,changeStage,ledger}`；`nodesApi/{add,rename,remove,attachments,upload,deleteAttachment,downloadUrl}`；`detailsApi/{purchases,addPurchase,delPurchase,acceptances,addAcceptance,delAcceptance}`；`statsApi/{get}`；`wan(v)`（元→万元字符串）、`toYuan(w)`（万元→元）

- [ ] **Step 1: 写工程文件并安装依赖**

`frontend/package.json`:
```json
{
  "name": "project-ledger-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": { "dev": "vite", "build": "vite build", "preview": "vite preview" },
  "dependencies": {
    "axios": "^1.7.9",
    "element-plus": "^2.9.1",
    "vue": "^3.5.13",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.2.1",
    "vite": "^5.4.11"
  }
}
```

`frontend/vite.config.js`:
```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 3000,
    proxy: { '/api': 'http://127.0.0.1:8000' }
  }
})
```

`frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>项目台账 · 一项目一本账</title>
</head>
<body><div id="app"></div><script type="module" src="/src/main.js"></script></body>
</html>
```

`frontend/src/main.js`:
```js
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'

createApp(App).use(ElementPlus).use(router).mount('#app')
```

`frontend/src/router.js`:
```js
import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'list', component: () => import('./views/ProjectList.vue') },
    { path: '/projects/:id', name: 'detail', component: () => import('./views/ProjectDetail.vue') },
    { path: '/stats', name: 'stats', component: () => import('./views/StatsView.vue') }
  ]
})
```

`frontend/src/App.vue`:
```vue
<template>
  <el-container style="min-height: 100vh">
    <el-header style="background: #1f4e9c; display: flex; align-items: center">
      <span style="color: #fff; font-size: 18px; font-weight: bold; margin-right: 32px">
        项目台账 · 一项目一本账
      </span>
      <el-menu :default-active="$route.path" mode="horizontal" router
               background-color="#1f4e9c" text-color="#dbe7f7"
               active-text-color="#ffffff" style="border: none">
        <el-menu-item index="/">项目列表</el-menu-item>
        <el-menu-item index="/stats">三口径统计</el-menu-item>
      </el-menu>
    </el-header>
    <el-main><router-view /></el-main>
  </el-container>
</template>
```

`frontend/src/api/index.js`:
```js
import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({ baseURL: '/api' })
http.interceptors.response.use(
  (res) => res,
  (err) => {
    ElMessage.error(err.response?.data?.message || err.message || '请求失败')
    return Promise.reject(err)
  }
)

export const wan = (v) => ((Number(v) || 0) / 10000).toFixed(2)      // 元 → 万元（显示）
export const toYuan = (w) => Math.round((Number(w) || 0) * 10000)    // 万元 → 元（提交）

export const projectsApi = {
  list: (params) => http.get('/projects', { params }),
  create: (data) => http.post('/projects', data),
  update: (id, data) => http.put(`/projects/${id}`, data),
  changeStage: (id, stage) => http.patch(`/projects/${id}/stage`, { stage }),
  ledger: (id) => http.get(`/projects/${id}/ledger`)
}

export const nodesApi = {
  add: (parentId, name) => http.post('/nodes', { parent_id: parentId, name }),
  rename: (id, name) => http.patch(`/nodes/${id}`, { name }),
  remove: (id) => http.delete(`/nodes/${id}`),
  attachments: (id) => http.get(`/nodes/${id}/attachments`),
  upload: (id, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post(`/nodes/${id}/attachments`, fd)
  },
  deleteAttachment: (id) => http.delete(`/attachments/${id}`),
  downloadUrl: (id) => `/api/attachments/${id}/download`
}

export const detailsApi = {
  purchases: (pid) => http.get(`/projects/${pid}/purchases`),
  addPurchase: (pid, data) => http.post(`/projects/${pid}/purchases`, data),
  delPurchase: (id) => http.delete(`/purchases/${id}`),
  acceptances: (pid) => http.get(`/projects/${pid}/acceptances`),
  addAcceptance: (pid, data) => http.post(`/projects/${pid}/acceptances`, data),
  delAcceptance: (id) => http.delete(`/acceptances/${id}`)
}

export const statsApi = { get: () => http.get('/stats') }
```

Run: `cd frontend; npm install` → 预期安装成功。

- [ ] **Step 2: 三占位页面（使路由可渲染，Task 10-12 逐个替换）**

创建 `frontend/src/views/ProjectList.vue`、`ProjectDetail.vue`、`StatsView.vue`，每个暂为：
```vue
<template><div>建设中（Task N 替换）</div></template>
```

Run: `npm run dev`，浏览器打开 `http://localhost:3000` → 菜单与占位页正常 → Ctrl+C。
（后端另窗口 `python -X utf8 -m uvicorn app.main:app --port 8000` 配合验证 `/api` 代理：临时在页面里 `fetch('/api/health')` 打印 ok 即可，验证后删除。）

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "feat: 前端骨架（Vite+Vue3+ElementPlus+路由+API封装+金额换算）"
```

---

### Task 10: 项目列表页（检索/筛选/新建/跳详情）

**Files:**
- Modify: `frontend/src/views/ProjectList.vue`（替换占位）

**Interfaces:**
- Consumes: `projectsApi.list/create`、`wan/toYuan`、`STAGES`（前端本地常量，与后端一致）
- Produces: 无（页面节点）

- [ ] **Step 1: 实现页面**

`frontend/src/views/ProjectList.vue`:
```vue
<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { projectsApi, wan, toYuan } from '../api'

const STAGES = ['商机', '中标', '签约', '立项', '采购', '实施', '交付', '验收', '结算']
const router = useRouter()
const rows = ref([])
const loading = ref(false)
const query = reactive({ keyword: '', stage: '' })
const dialog = ref(false)
const form = reactive({ name: '', customer: '', contract_no: '', owner: '',
                        amount_wan: 0, initial_stage: '商机' })

async function load() {
  loading.value = true
  try {
    const { data } = await projectsApi.list({
      keyword: query.keyword || undefined,
      stage: query.stage || undefined
    })
    rows.value = data
  } finally { loading.value = false }
}

async function create() {
  if (!form.name.trim()) return
  await projectsApi.create({
    name: form.name.trim(), customer: form.customer, contract_no: form.contract_no,
    owner: form.owner, contract_amount: toYuan(form.amount_wan),
    initial_stage: form.initial_stage
  })
  dialog.value = false
  Object.assign(form, { name: '', customer: '', contract_no: '', owner: '',
                        amount_wan: 0, initial_stage: '商机' })
  load()
}

onMounted(load)
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 12px">
      <el-input v-model="query.keyword" placeholder="按项目名称检索…" clearable
                style="width: 260px" @input="load" />
      <el-select v-model="query.stage" placeholder="按当前阶段筛选" clearable
                 style="width: 180px" @change="load">
        <el-option v-for="s in STAGES" :key="s" :label="s" :value="s" />
      </el-select>
      <el-button type="primary" @click="dialog = true">＋ 新建项目</el-button>
    </div>

    <el-table :data="rows" v-loading="loading" border stripe
              highlight-current-row @row-click="(r) => router.push(`/projects/${r.id}`)">
      <el-table-column prop="name" label="项目名称" min-width="220" />
      <el-table-column prop="customer" label="客户" min-width="140" />
      <el-table-column prop="contract_no" label="合同编号" min-width="120" />
      <el-table-column label="当前阶段" width="90">
        <template #default="{ row }">
          <el-tag type="primary" effect="light">{{ row.current_stage }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="签约额(万元)" width="120" align="right">
        <template #default="{ row }">{{ wan(row.contract_amount) }}</template>
      </el-table-column>
      <el-table-column prop="owner" label="负责人" width="90" />
    </el-table>
    <el-empty v-if="!loading && !rows.length" description="暂无项目，点右上角新建或从Excel录入皆可" />

    <el-dialog v-model="dialog" title="新建项目（可选任意起始阶段，承接存量）" width="520">
      <el-form label-width="90px">
        <el-form-item label="项目名称" required>
          <el-input v-model="form.name" placeholder="必填" />
        </el-form-item>
        <el-form-item label="客户"><el-input v-model="form.customer" /></el-form-item>
        <el-form-item label="合同编号"><el-input v-model="form.contract_no" /></el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.owner" /></el-form-item>
        <el-form-item label="签约额(万元)">
          <el-input-number v-model="form.amount_wan" :min="0" :controls="false" style="width: 200px" />
        </el-form-item>
        <el-form-item label="起始阶段">
          <el-select v-model="form.initial_stage" style="width: 200px">
            <el-option v-for="s in STAGES" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" @click="create">创建台账</el-button>
      </template>
    </el-dialog>
  </div>
</template>
```

- [ ] **Step 2: 浏览器验证**

后端起 8000、前端 `npm run dev`，打开 `http://localhost:3000`：
1) 新建项目（起始阶段=采购、签约额 860 万）→ 列表出现该行
2) 检索关键字 → 过滤生效；阶段筛选 → 过滤生效
3) 点行 → 跳转详情路由（占位页）

Expected: 全部通过后 Ctrl+C。

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "feat: 项目列表页（名称检索/阶段筛选/任意阶段新建）"
```

---

### Task 11: 项目详情页（一账制：概要+阶段流转+环节树附件+明细表）

**Files:**
- Create: `frontend/src/components/StageStepper.vue`, `frontend/src/components/NodeTreePanel.vue`, `frontend/src/components/DetailTables.vue`
- Modify: `frontend/src/views/ProjectDetail.vue`（替换占位）

**Interfaces:**
- Consumes: `projectsApi.ledger/changeStage`、`nodesApi.*`、`detailsApi.*`、`wan/toYuan`、`STAGES`
- Produces: `StageStepper(props: stages, current, initial; emit: select(stage))`；`NodeTreePanel(props: tree; emit: changed)`（自管附件增删）；`DetailTables(props: projectId, purchases, acceptances, totals; emit: changed)`

- [ ] **Step 1: StageStepper 组件**

`frontend/src/components/StageStepper.vue`:
```vue
<script setup>
defineProps({
  stages: { type: Array, required: true },
  current: String,
  initial: String
})
const emit = defineEmits(['select'])
</script>

<template>
  <div style="display: flex; gap: 4px">
    <div v-for="(s, i) in stages" :key="s" class="step"
         :class="{ current: s === current,
                   excluded: i < stages.indexOf(initial),
                   reached: i >= stages.indexOf(initial) && i <= stages.indexOf(current) }"
         @click="emit('select', s)">
      <span class="idx">{{ i + 1 }}</span>{{ s }}
      <span v-if="s === current" class="tag">当前</span>
      <span v-else-if="i < stages.indexOf(initial)" class="tag dim">存量未纳入</span>
    </div>
  </div>
</template>

<style scoped>
.step { flex: 1; text-align: center; padding: 8px 2px; border-bottom: 3px solid #dcdfe6;
        cursor: pointer; font-size: 13px; color: #606266; user-select: none; }
.step .idx { display: block; font-size: 11px; color: #909399; }
.step:hover { background: #f5f7fa; }
.step.reached { border-bottom-color: #a0c6ff; }
.step.current { border-bottom-color: #1f4e9c; font-weight: bold; color: #1f4e9c; background: #ecf2fb; }
.step.excluded { border-bottom-style: dashed; color: #c0c4cc; }
.tag { display: block; font-size: 10px; color: #e6a23c; }
.tag.dim { color: #c0c4cc; }
</style>
```

- [ ] **Step 2: NodeTreePanel 组件（树+附件管理）**

`frontend/src/components/NodeTreePanel.vue`:
```vue
<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { nodesApi } from '../api'

const props = defineProps({ tree: { type: Array, required: true } })
const emit = defineEmits(['changed'])

function onAdd(data) {
  ElMessageBox.prompt('子环节名称（可继续嵌套）', `在【${data.name}】下新增`).then(({ value }) => {
    if (!value) return
    nodesApi.add(data.id, value.trim()).then(() => emit('changed'))
  }).catch(() => {})
}

function onRename(data) {
  ElMessageBox.prompt('新名称', '重命名', { inputValue: data.name }).then(({ value }) => {
    if (!value) return
    nodesApi.rename(data.id, value.trim()).then(() => emit('changed'))
  }).catch(() => {})
}

function onDelete(data) {
  ElMessageBox.confirm(`确认删除环节【${data.name}】？（有子环节或附件时会被系统拒绝）`, '删除')
    .then(() => nodesApi.remove(data.id).then(() => emit('changed')))
    .catch(() => {})
}

// 附件抽屉
const drawer = ref(false)
const currentNode = ref(null)
const attachments = ref([])
const uploadInput = ref(null)

function openAttachments(data) {
  currentNode.value = data
  drawer.value = true
  loadAttachments()
}

async function loadAttachments() {
  const { data } = await nodesApi.attachments(currentNode.value.id)
  attachments.value = data
}

function triggerUpload() { uploadInput.value?.click() }

async function doUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  await nodesApi.upload(currentNode.value.id, file)
  e.target.value = ''
  ElMessage.success('已上传')
  loadAttachments()
  emit('changed')
}

function onDeleteAttachment(att) {
  ElMessageBox.confirm(`删除附件【${att.original_name}】？`, '删除附件')
    .then(async () => { await nodesApi.deleteAttachment(att.id); loadAttachments(); emit('changed') })
    .catch(() => {})
}
</script>

<template>
  <div>
    <el-tree :data="tree" node-key="id" default-expand-all
             :props="{ label: 'name', children: 'children' }">
      <template #default="{ data }">
        <div style="display: flex; align-items: center; gap: 6px; flex: 1">
          <span :style="data.is_anchor ? 'font-weight: bold' : ''">
            {{ data.is_anchor ? '📌 ' : '' }}{{ data.name }}
          </span>
          <el-tag v-if="data.attachment_count" size="small" type="success" effect="light"
                  style="cursor: pointer" @click.stop="openAttachments(data)">
            📎{{ data.attachment_count }}
          </el-tag>
          <el-button size="small" text type="primary" @click.stop="openAttachments(data)">
            附件
          </el-button>
          <el-button size="small" text type="primary" @click.stop="onAdd(data)">+子环节</el-button>
          <template v-if="!data.is_anchor">
            <el-button size="small" text @click.stop="onRename(data)">改名</el-button>
            <el-button size="small" text type="danger" @click.stop="onDelete(data)">删</el-button>
          </template>
        </div>
      </template>
    </el-tree>

    <el-drawer v-model="drawer" :title="currentNode ? `【${currentNode.name}】附件` : '附件'"
               size="40%">
      <input ref="uploadInput" type="file" style="display: none" @change="doUpload" />
      <el-button type="primary" style="margin-bottom: 10px" @click="triggerUpload">
        上传附件
      </el-button>
      <el-table :data="attachments" border size="small">
        <el-table-column prop="original_name" label="文件名" min-width="200" />
        <el-table-column label="大小" width="100">
          <template #default="{ row }">{{ (row.size / 1024).toFixed(0) }} KB</template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-link type="primary" :href="`/api/attachments/${row.id}/download`"
                     target="_blank">下载</el-link>
            <el-button size="small" text type="danger" style="margin-left: 8px"
                       @click="onDeleteAttachment(row)">删</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>
```

- [ ] **Step 3: DetailTables 组件（采购/验收两张表）**

`frontend/src/components/DetailTables.vue`:
```vue
<script setup>
import { reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { detailsApi, wan, toYuan } from '../api'

const props = defineProps({
  projectId: Number,
  purchases: Array,
  acceptances: Array,
  totals: Object
})
const emit = defineEmits(['changed'])

const purDialog = ref(false)
const purForm = reactive({ name: '', supplier: '', amount_wan: 0 })
async function addPurchase() {
  if (!purForm.name.trim()) return
  await detailsApi.addPurchase(props.projectId, {
    name: purForm.name.trim(), supplier: purForm.supplier,
    amount: toYuan(purForm.amount_wan)
  })
  purDialog.value = false
  Object.assign(purForm, { name: '', supplier: '', amount_wan: 0 })
  emit('changed')
}
function delPurchase(row) {
  ElMessageBox.confirm(`删除采购单【${row.name}】？`, '删除')
    .then(() => detailsApi.delPurchase(row.id).then(() => emit('changed')))
    .catch(() => {})
}

const accDialog = ref(false)
const accForm = reactive({ name: '', received_wan: 0 })
async function addAcceptance() {
  if (!accForm.name.trim()) return
  await detailsApi.addAcceptance(props.projectId, {
    name: accForm.name.trim(), received_amount: toYuan(accForm.received_wan)
  })
  accDialog.value = false
  Object.assign(accForm, { name: '', received_wan: 0 })
  emit('changed')
}
function delAcceptance(row) {
  ElMessageBox.confirm(`删除验收记录【${row.name}】？`, '删除')
    .then(() => detailsApi.delAcceptance(row.id).then(() => emit('changed')))
    .catch(() => {})
}
</script>

<template>
  <div>
    <div style="display: flex; align-items: center; margin-bottom: 6px">
      <b>采购明细（后向口径）</b>
      <el-button size="small" type="primary" text @click="purDialog = true">＋加采购</el-button>
      <span style="margin-left: auto; font-size: 13px">
        采购额合计：<b style="color: #1f4e9c">{{ wan(totals?.purchase_amount) }}</b> 万元
      </span>
    </div>
    <el-table :data="purchases" border size="small">
      <el-table-column prop="name" label="采购名称" min-width="140" />
      <el-table-column prop="supplier" label="供应商" min-width="110" />
      <el-table-column label="金额(万元)" width="110" align="right">
        <template #default="{ row }">{{ wan(row.amount) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="70">
        <template #default="{ row }">
          <el-button size="small" text type="danger" @click="delPurchase(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="display: flex; align-items: center; margin: 14px 0 6px">
      <b>验收记录（交付口径）</b>
      <el-button size="small" type="primary" text @click="accDialog = true">＋加验收</el-button>
      <span style="margin-left: auto; font-size: 13px">
        回款额合计：<b style="color: #1f4e9c">{{ wan(totals?.received_amount) }}</b> 万元
      </span>
    </div>
    <el-table :data="acceptances" border size="small">
      <el-table-column prop="name" label="验收名称" min-width="140" />
      <el-table-column label="回款金额(万元)" width="120" align="right">
        <template #default="{ row }">{{ wan(row.received_amount) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="70">
        <template #default="{ row }">
          <el-button size="small" text type="danger" @click="delAcceptance(row)">删</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="purDialog" title="新增采购单" width="420">
      <el-form label-width="80px">
        <el-form-item label="名称" required><el-input v-model="purForm.name" /></el-form-item>
        <el-form-item label="供应商"><el-input v-model="purForm.supplier" /></el-form-item>
        <el-form-item label="金额(万元)">
          <el-input-number v-model="purForm.amount_wan" :min="0" :controls="false" style="width: 180px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="purDialog = false">取消</el-button>
        <el-button type="primary" @click="addPurchase">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="accDialog" title="新增验收记录" width="420">
      <el-form label-width="90px">
        <el-form-item label="验收名称" required><el-input v-model="accForm.name" /></el-form-item>
        <el-form-item label="回款(万元)">
          <el-input-number v-model="accForm.received_wan" :min="0" :controls="false" style="width: 180px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="accDialog = false">取消</el-button>
        <el-button type="primary" @click="addAcceptance">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
```

- [ ] **Step 4: ProjectDetail 页面（组装一账）**

`frontend/src/views/ProjectDetail.vue`:
```vue
<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { projectsApi, wan } from '../api'
import StageStepper from '../components/StageStepper.vue'
import NodeTreePanel from '../components/NodeTreePanel.vue'
import DetailTables from '../components/DetailTables.vue'

const STAGES = ['商机', '中标', '签约', '立项', '采购', '实施', '交付', '验收', '结算']
const route = useRoute()
const ledger = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const { data } = await projectsApi.ledger(route.params.id)
    ledger.value = data
  } finally { loading.value = false }
}

function onSelectStage(stage) {
  const p = ledger.value.project
  if (stage === p.current_stage) return
  if (STAGES.indexOf(stage) < STAGES.indexOf(p.initial_stage)) {
    ElMessageBox.confirm(`【${stage}】在起始阶段【${p.initial_stage}】之前，通常为存量未纳入阶段，仍要流转吗？`)
      .then(() => doChange(stage)).catch(() => {})
  } else {
    doChange(stage)
  }
}

async function doChange(stage) {
  await projectsApi.changeStage(ledger.value.project.id, stage)
  load()
}

onMounted(load)
const p = computed(() => ledger.value?.project)
</script>

<template>
  <div v-loading="loading">
    <template v-if="p">
      <el-card style="margin-bottom: 12px">
        <div style="display: flex; align-items: center; gap: 18px; flex-wrap: wrap">
          <b style="font-size: 17px">{{ p.name }}</b>
          <span style="color: #909399">客户：{{ p.customer || '—' }}</span>
          <span style="color: #909399">合同编号：{{ p.contract_no || '—' }}</span>
          <span style="color: #909399">负责人：{{ p.owner || '—' }}</span>
          <span style="margin-left: auto">
            签约额：<b style="color: #1f4e9c; font-size: 16px">{{ wan(p.contract_amount) }}</b> 万元
          </span>
        </div>
      </el-card>

      <el-card style="margin-bottom: 12px">
        <StageStepper :stages="STAGES" :current="p.current_stage" :initial="p.initial_stage"
                      @select="onSelectStage" />
        <div style="font-size: 12px; color: #909399; margin-top: 6px">
          起始阶段：<b>{{ p.initial_stage }}</b>｜点击阶段可流转（推进/回退/跳转），回退不影响左侧资料树
        </div>
      </el-card>

      <el-row :gutter="12">
        <el-col :span="10">
          <el-card>
            <template #header><b>环节树（按环节归档资料）</b></template>
            <NodeTreePanel :tree="ledger.tree" @changed="load" />
          </el-card>
        </el-col>
        <el-col :span="14">
          <el-card>
            <DetailTables :project-id="p.id" :purchases="ledger.purchases"
                          :acceptances="ledger.acceptances" :totals="ledger.totals"
                          @changed="load" />
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>
```

- [ ] **Step 5: 浏览器验证（关键路径逐一目检）**

1) 详情页打开 → 概要条/9 阶段步进条/9 锚点树/两张明细表齐全
2) 点"实施"→ 流转成功，当前标记移动；点起始前阶段 → 弹确认
3) 采购锚点下建"硬件采购"→ 建二级"二标段" → 挂一个 PDF 附件 → 树上 📎1 → 下载内容一致 → 删除
4) 删"硬件采购"（含子环节）→ 红色 toast"先清空子环节"；清空后再删成功
5) 加采购 120 万 + 80 万 → 合计 200 万；加验收 300 万 → 合计 300 万

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat: 项目详情页一账制（概要/阶段流转/环节树附件/采购验收明细）"
```

---

### Task 12: 统计页（三口径卡片 + 导出）

**Files:**
- Modify: `frontend/src/views/StatsView.vue`（替换占位）

**Interfaces:**
- Consumes: `statsApi.get`、`wan`

- [ ] **Step 1: 实现页面**

`frontend/src/views/StatsView.vue`:
```vue
<script setup>
import { onMounted, ref } from 'vue'
import { statsApi, wan } from '../api'

const stats = ref(null)

function load() { statsApi.get().then(({ data }) => (stats.value = data)) }

onMounted(load)

const cards = [
  { key: 'forward', title: '前向 · 签约口径', sub: '有签约额项目' },
  { key: 'backward', title: '后向 · 采购口径', sub: '有采购单项目' },
  { key: 'deliver', title: '交付 · 回款口径', sub: '有验收回款项目' }
]
</script>

<template>
  <div v-if="stats">
    <el-row :gutter="14" style="margin-bottom: 14px">
      <el-col v-for="c in cards" :key="c.key" :span="8">
        <el-card>
          <div style="font-size: 13px; color: #909399">{{ c.title }}</div>
          <div style="font-size: 28px; font-weight: bold; color: #1f4e9c; margin: 6px 0">
            {{ wan(stats[c.key].amount) }} <span style="font-size: 14px">万元</span>
          </div>
          <div style="font-size: 12px; color: #606266">
            {{ c.sub }} {{ stats[c.key].count }} 个
          </div>
        </el-card>
      </el-col>
    </el-row>
    <el-button type="primary" @click="window.open('/api/stats/export')">
      导出三口径明细 Excel
    </el-button>
    <div style="color: #909399; font-size: 12px; margin-top: 8px">
      口径说明：前向=项目签约额；后向=Σ采购单金额；交付=Σ验收回款金额（均有明细聚合，只算不存）
    </div>
  </div>
</template>
```

> 注意：模板里 `window` 不可直接用，改为 `@click="() => window.open(...)"` 行不通（Vue 模板作用域无 window）——实际实现用 methods：`function exportFile() { window.open('/api/stats/export') }`，按钮 `@click="exportFile"`。（编码时以此为准。）

- [ ] **Step 2: 浏览器验证**

打开 `/stats`：三卡片显示（沿用 Task 11 造的数据），点击导出 → 下载 xlsx，用 Excel/WPS 打开确认 3 个 sheet。

- [ ] **Step 3: Commit**

```bash
git add frontend
git commit -m "feat: 三口径统计卡片与Excel导出"
```

---

### Task 13: 一键启动 + 联调验收 + 文档收尾

**Files:**
- Create: `backend/start.ps1` 或项目根 `start.ps1`
- Modify: `README.md`（运行说明）

**Interfaces:**
- Consumes: 全部
- Produces: `start.ps1`（一键拉起后端 8000 + 前端 3000 并自动打开浏览器）

- [ ] **Step 1: 写一键启动脚本（项目根 `start.ps1`）**

```powershell
# 项目台账 一键启动：后端8000 + 前端3000
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$py = "python"

# 依赖自检/安装（首次）
if (-not (Test-Path "$root\backend\.deps_installed")) {
  & $py -m pip install -r "$root\backend\requirements.txt"
  New-Item -ItemType File -Path "$root\backend\.deps_installed" | Out-Null
}

# 后端
Start-Process -FilePath $py -ArgumentList "-X","utf8","-m","uvicorn","app.main:app","--port","8000" `
  -WorkingDirectory "$root\backend" -WindowStyle Minimized

# 前端
if (-not (Test-Path "$root\frontend\node_modules")) {
  Push-Location "$root\frontend"; npm install; Pop-Location
}
Start-Process -FilePath "cmd" -ArgumentList "/c","npm","run","dev" `
  -WorkingDirectory "$root\frontend" -WindowStyle Minimized

Start-Sleep -Seconds 4
Start-Process "http://localhost:3000"
```

- [ ] **Step 2: 全量回归**

Run: `cd backend; python -X utf8 -m pytest tests -v`
Expected: 全部 PASS

- [ ] **Step 3: 端到端验收（对照技术规格 23 条用户故事逐条过）**

双击/执行 `start.ps1` → 按 PRD 验收标准完整走一遍：新建（任意阶段）→ 流转（推进/回退）→ 子环节嵌套 3 层 → 附件上传下载删除 → 删除保护提示 → 采购/验收增删 → 检索 → 统计三卡片数值核对 → 导出打开。

- [ ] **Step 4: README 更新 + 收尾提交**

README 补：运行方式（`start.ps1`）、技术栈、数据目录说明（`data/` 为库+附件，整体拷贝即备份）。

```bash
git add start.ps1 README.md
git commit -m "feat: 一键启动脚本与README运行说明"
git push origin main
```

---

## 验收标准（对照技术规格）

1. `pytest` 全绿（storage/tree/project/detail/stats/api 全套）。
2. 原型验证文档 5 条决策全部落地：非空禁删 409、存量未纳入标记、回退不动树、三口径有数项目数口径、万元交互/元存储。
3. 23 条用户故事浏览器逐条可走通。
4. `start.ps1` 一键可跑；`data/` 目录拷贝即完成备份。

## Self-Review 结论

- 规格覆盖：FR-1~FR-11 分别落 Task 2/1/5/5/6/6/4/8/10/7+12/9；US-001~008 全覆盖；范围外未实现项（认证/导入/图表）与 Non-Goals 一致。
- 类型一致性：`NodeOut.attachment_count`、`LedgerOut.totals`、金额接口（services Decimal / DTO float / 前端 wan-toYuan）已对齐；计划内两处"编码时以××为准"的提示（get_ledger 顶部导入、StatsView 导出方法）已在任务中就地注明明晰写法。
- 占位符扫描：无 TBD/TODO；测试与实现均给全码。