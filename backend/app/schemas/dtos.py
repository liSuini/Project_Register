from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- 项目 ----------
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


# ---------- 环节树 ----------
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


# ---------- 采购 ----------
class PurchaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    supplier: str = ""
    amount: float = 0                     # 元
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


# ---------- 验收 ----------
class AcceptanceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    acceptance_date: Optional[date] = None
    received_amount: float = 0            # 元
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


# ---------- 统计与一账 ----------
class CaliberItem(BaseModel):
    count: int
    amount: float                         # 元


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
