from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document_text_block import DocumentTextBlock
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/coverage")
def get_coverage(db: Session = Depends(get_db)):
    total_documents = db.query(SourceDocument).count()

    total_documents_with_text = (
        db.query(DocumentTextBlock.source_document_id)
        .distinct()
        .count()
    )

    sources_rows = (
        db.query(
            SourceDocument.source_name,
            func.count(SourceDocument.id),
        )
        .group_by(SourceDocument.source_name)
        .order_by(SourceDocument.source_name)
        .all()
    )
    sources_attempted = [row[0] for row in sources_rows]

    total_records_by_source = {
        row[0]: row[1] for row in sources_rows
    }

    date_range_rows = (
        db.query(
            func.min(SourceDocument.retrieved_at),
            func.max(SourceDocument.retrieved_at),
        )
        .filter(SourceDocument.retrieved_at.isnot(None))
        .first()
    )
    date_ranges_attempted = []
    if date_range_rows and date_range_rows[0] and date_range_rows[1]:
        date_ranges_attempted.append({
            "start": date_range_rows[0].isoformat() if hasattr(date_range_rows[0], "isoformat") else str(date_range_rows[0]),
            "end": date_range_rows[1].isoformat() if hasattr(date_range_rows[1], "isoformat") else str(date_range_rows[1]),
        })

    last_run = (
        db.query(IngestionRun)
        .order_by(IngestionRun.created_at.desc())
        .first()
    )
    last_successful_run = None
    if last_run:
        last_successful_run = {
            "id": last_run.id,
            "source": last_run.source_name,
            "status": last_run.run_status,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
            "completed_at": last_run.finished_at.isoformat() if last_run.finished_at else None,
            "records_found": last_run.records_found,
            "records_saved": last_run.records_saved,
        }

    return {
        "historical_backfill_status": "partial",
        "message": "Full historical APHIS coverage is not complete yet. Current data reflects available ingestion runs and stored documents only.",
        "total_documents": total_documents,
        "total_documents_with_text": total_documents_with_text,
        "sources_attempted": sources_attempted,
        "date_ranges_attempted": date_ranges_attempted,
        "total_records_by_source": total_records_by_source,
        "last_successful_run": last_successful_run,
        "coverage_snapshots": [],
        "coverage_snapshots_note": "Coverage snapshots table not yet implemented; data inferred from source_documents and ingestion_runs.",
        "historical_backfill_details": "Historical backfill is currently partial. The system supports controlled source/date-range backfill with logging, deduplication, raw preservation, and extraction tracking. Full historical completion should only be marked complete after source coverage is validated against ingestion run logs.",
    }