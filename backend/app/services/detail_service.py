from decimal import Decimal

from sqlalchemy.orm import Session

from app.errors import InvalidError, NotFoundError
from app.models.entities import AcceptanceRecord, Project, PurchaseOrder
from app.schemas.dtos import (AcceptanceCreate, AcceptanceUpdate,
                              PurchaseCreate, PurchaseUpdate)


def _ensure_project(db: Session, project_id: int) -> None:
    if db.get(Project, project_id) is None:
        raise NotFoundError("项目不存在")


# ---------- 采购单 ----------
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
    db.add(row)
    db.commit()
    db.refresh(row)
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
    db.commit()
    db.refresh(row)
    return row


def delete_purchase(db: Session, purchase_id: int) -> None:
    row = db.get(PurchaseOrder, purchase_id)
    if row is None:
        raise NotFoundError("采购单不存在")
    db.delete(row)
    db.commit()


# ---------- 验收记录 ----------
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
    db.add(row)
    db.commit()
    db.refresh(row)
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
    db.commit()
    db.refresh(row)
    return row


def delete_acceptance(db: Session, acceptance_id: int) -> None:
    row = db.get(AcceptanceRecord, acceptance_id)
    if row is None:
        raise NotFoundError("验收记录不存在")
    db.delete(row)
    db.commit()
