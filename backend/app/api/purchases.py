from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import (PurchaseCreate, PurchaseOut, PurchaseUpdate)
from app.services import detail_service as ds

router = APIRouter(tags=["purchases"])


@router.get("/api/projects/{project_id}/purchases",
            response_model=list[PurchaseOut])
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
