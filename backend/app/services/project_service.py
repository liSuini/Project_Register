from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import STAGES
from app.errors import InvalidError, NotFoundError
from app.models.entities import AcceptanceRecord, Project, PurchaseOrder, StageHistory
from app.schemas.dtos import (AcceptanceOut, LedgerOut, LedgerTotals,
                              ProjectCreate, ProjectOut, ProjectUpdate,
                              PurchaseOut)
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
                initial_stage=data.initial_stage,
                current_stage=data.initial_stage,
                start_date=data.start_date, end_date=data.end_date,
                note=data.note)
    db.add(p)
    db.commit()
    db.refresh(p)
    tree_service.create_project_tree(db, p.id)   # 自动生成 9 锚点（ADR-0002）
    return p


def search_projects(db: Session, keyword: str = "",
                    stage: str | None = None) -> list[Project]:
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
    """推进/回退/跳转皆可，写流转史；阶段不变化时不产生历史。"""
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
    """一账聚合：项目+树+采购+验收+合计，一个请求取全。"""
    p = _get_project(db, project_id)
    tree = tree_service.get_tree(db, project_id)
    purchases = (db.query(PurchaseOrder).filter_by(project_id=project_id)
                 .order_by(PurchaseOrder.id).all())
    acceptances = (db.query(AcceptanceRecord).filter_by(project_id=project_id)
                   .order_by(AcceptanceRecord.id).all())
    purchase_sum = db.query(
        func.coalesce(func.sum(PurchaseOrder.amount), 0)) \
        .filter_by(project_id=project_id).scalar()
    received_sum = db.query(
        func.coalesce(func.sum(AcceptanceRecord.received_amount), 0)) \
        .filter_by(project_id=project_id).scalar()
    return LedgerOut(
        project=ProjectOut.model_validate(p),
        tree=tree,
        purchases=[PurchaseOut.model_validate(x) for x in purchases],
        acceptances=[AcceptanceOut.model_validate(x) for x in acceptances],
        totals=LedgerTotals(purchase_amount=float(purchase_sum),
                            received_amount=float(received_sum)))
