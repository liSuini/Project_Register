from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import (ProjectCreate, ProjectOut, ProjectUpdate,
                              StageChange)
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
