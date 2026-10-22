from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import STAGES
from app.errors import ConflictError, NotFoundError
from app.models.entities import Attachment, Node
from app.schemas.dtos import NodeOut


def create_project_tree(db: Session, project_id: int) -> None:
    """项目创建时调用：生成 9 个阶段锚点（ADR-0002）。"""
    for i, stage in enumerate(STAGES):
        db.add(Node(project_id=project_id, parent_id=None,
                    name=stage, stage_key=stage, sort_order=i))
    db.commit()


def get_tree(db: Session, project_id: int) -> list[NodeOut]:
    """整树一次查询组装，含各节点附件计数。"""
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
