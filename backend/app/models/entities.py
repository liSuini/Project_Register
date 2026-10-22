from datetime import datetime
from decimal import Decimal

from sqlalchemy import (Column, Date, DateTime, ForeignKey, Integer, Numeric,
                        String, Text)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Project(Base):
    """台账主实体：一个项目一本账。"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    customer = Column(String(200), default="")
    contract_no = Column(String(100), default="")
    owner = Column(String(50), default="")
    contract_amount = Column(Numeric(14, 2), default=Decimal("0"))  # 签约额(元)
    initial_stage = Column(String(20), nullable=False)   # 起始阶段（存量起步语义）
    current_stage = Column(String(20), nullable=False)   # 当前阶段（统计/流转口径）
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    nodes = relationship("Node", cascade="all, delete-orphan",
                         passive_deletes=True)


class Node(Base):
    """环节树节点：锚点(parent为空+stage_key有值)或用户子环节，任意嵌套。"""
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=False)
    parent_id = Column(Integer, ForeignKey("nodes.id"), nullable=True)
    name = Column(String(200), nullable=False)
    stage_key = Column(String(20), nullable=True)   # 9 锚点有值
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    children = relationship("Node", cascade="all, delete-orphan",
                            passive_deletes=True)


class Attachment(Base):
    """附件元数据；物理文件在本机 uploads 目录（ADR-0003）。"""
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), index=True, nullable=False)
    original_name = Column(String(500), nullable=False)
    stored_path = Column(String(500), nullable=False)   # {pid}/{uuid}{ext} 相对路径
    size = Column(Integer, default=0)
    mime = Column(String(100), default="")
    uploaded_at = Column(DateTime, default=datetime.now)


class PurchaseOrder(Base):
    """采购单：项目平级明细（ADR-0004），后向口径来源。"""
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
    """验收记录：项目平级明细（ADR-0004），交付口径来源。"""
    __tablename__ = "acceptance_records"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=False)
    name = Column(String(200), nullable=False)
    acceptance_date = Column(Date, nullable=True)
    received_amount = Column(Numeric(14, 2), default=Decimal("0"))   # 元
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)


class StageHistory(Base):
    """阶段流转史：每次推进/回退/跳转一条。"""
    __tablename__ = "stage_histories"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), index=True, nullable=False)
    from_stage = Column(String(20), nullable=False)
    to_stage = Column(String(20), nullable=False)
    changed_at = Column(DateTime, default=datetime.now)
