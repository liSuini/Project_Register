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
