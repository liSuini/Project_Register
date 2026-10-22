from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dtos import StatsOut
from app.services import stats_service

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    return stats_service.calibers(db)


@router.get("/export")
def export(db: Session = Depends(get_db)):
    content = stats_service.export_xlsx(db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument"
                   ".spreadsheetml.sheet",
        headers={"Content-Disposition":
                 "attachment; filename=ledger-report.xlsx"})
