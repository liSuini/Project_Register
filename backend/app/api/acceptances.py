from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import (AcceptanceCreate, AcceptanceOut,
                              AcceptanceUpdate)
from app.services import detail_service as ds

router = APIRouter(tags=["acceptances"])


@router.get("/api/projects/{project_id}/acceptances",
            response_model=list[AcceptanceOut])
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
