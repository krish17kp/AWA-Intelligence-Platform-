from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ingestion_event import IngestionEvent
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
        "run_type": getattr(run, 'run_type', None) or "manual",
        "status": run.run_status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.finished_at.isoformat() if run.finished_at else None,
        "records_found": run.records_found,
        "new_documents": getattr(run, 'new_documents', 0) or run.records_saved or 0,
        "duplicates_skipped": getattr(run, 'duplicates_skipped', 0) or 0,
        "failed_documents": getattr(run, 'failed_documents', 0) or 0,
        "date_range_start": run.date_range_start.isoformat() if hasattr(run, 'date_range_start') and run.date_range_start else None,
        "date_range_end": run.date_range_end.isoformat() if hasattr(run, 'date_range_end') and run.date_range_end else None,
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


@router_v2.get("/runs/{run_id}/events")
def get_ingestion_run_events(run_id: int, db: Session = Depends(get_db)):
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Ingestion run not found")

    events = (
        db.query(IngestionEvent)
        .filter(IngestionEvent.run_id == run_id)
        .order_by(IngestionEvent.created_at.asc())
        .all()
    )

    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "message": event.message,
            "document_id": event.document_id,
            "payload": event.payload,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in events
    ]