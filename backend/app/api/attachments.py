from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_storage
from app.core.database import get_db
from app.errors import NotFoundError
from app.models.entities import Attachment, Node
from app.schemas.dtos import AttachmentOut
from app.services.storage import LocalFilesystemStorage

router = APIRouter(tags=["attachments"])


@router.post("/api/nodes/{node_id}/attachments", status_code=201,
             response_model=AttachmentOut)
def upload_attachment(node_id: int, file: UploadFile = File(...),
                      db: Session = Depends(get_db),
                      storage: LocalFilesystemStorage = Depends(get_storage)):
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
                        storage: LocalFilesystemStorage = Depends(get_storage)):
    att = db.get(Attachment, att_id)
    if att is None:
        raise NotFoundError("附件不存在")
    return FileResponse(storage.open_path(att.stored_path),
                        filename=att.original_name)


@router.delete("/api/attachments/{att_id}", status_code=204)
def delete_attachment(att_id: int, db: Session = Depends(get_db),
                      storage: LocalFilesystemStorage = Depends(get_storage)):
    att = db.get(Attachment, att_id)
    if att is None:
        raise NotFoundError("附件不存在")
    db.delete(att)
    db.commit()
    storage.remove(att.stored_path)   # 先删记录再删文件，物理缺失容忍
    return None
