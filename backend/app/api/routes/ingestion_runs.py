from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ingestion_run import IngestionRun

router_v1 = APIRouter(prefix="/ingestion-runs", tags=["ingestion-runs"])
router_v2 = APIRouter(prefix="/ingestion", tags=["ingestion-runs"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_to_response_item(run: IngestionRun) -> dict:
    return {
        "run_id": run.id,
        "source": run.source_name,
        "run_type": None,
        "status": run.run_status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.finished_at.isoformat() if run.finished_at else None,
        "records_found": run.records_found,
        "new_documents": run.records_saved,
        "duplicates_skipped": 0,
        "failed_documents": 0,
        "date_range_start": None,
        "date_range_end": None,
        "error_message": run.error_message,
    }


@router_v1.get("")
def list_ingestion_runs(limit: int = 20, db: Session = Depends(get_db)):
    if limit > 100:
        limit = 100

    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.created_at.desc())
        .limit(limit)
        .all()
    )

    return [_run_to_response_item(run) for run in runs]


@router_v2.get("/runs")
def list_ingestion_runs_v2(limit: int = 20, db: Session = Depends(get_db)):
    if limit > 100:
        limit = 100

    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.created_at.desc())
        .limit(limit)
        .all()
    )

    return [_run_to_response_item(run) for run in runs]