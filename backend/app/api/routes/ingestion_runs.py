from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ingestion_run import IngestionRun

router = APIRouter(prefix="/ingestion-runs", tags=["ingestion-runs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def list_ingestion_runs(limit: int = 20, db: Session = Depends(get_db)):
    if limit > 100:
        limit = 100

    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": run.id,
            "source_name": run.source_name,
            "run_status": run.run_status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "records_found": run.records_found,
            "records_saved": run.records_saved,
            "error_message": run.error_message,
            "created_at": run.created_at,
        }
        for run in runs
    ]