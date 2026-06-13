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


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    total_documents = db.query(SourceDocument).count()

    total_raw_files_preserved = (
        db.query(SourceDocument)
        .filter(SourceDocument.storage_path.isnot(None))
        .filter(SourceDocument.storage_path != "")
        .count()
    )

    total_documents_with_text = (
        db.query(DocumentTextBlock.source_document_id)
        .distinct()
        .count()
    )

    total_ingestion_runs = db.query(IngestionRun).count()

    latest_run = (
        db.query(IngestionRun)
        .order_by(IngestionRun.created_at.desc())
        .first()
    )

    latest_ingestion_run = None
    if latest_run:
        latest_ingestion_run = {
            "id": latest_run.id,
            "source": latest_run.source_name,
            "status": latest_run.run_status,
            "started_at": latest_run.started_at.isoformat() if latest_run.started_at else None,
            "completed_at": latest_run.finished_at.isoformat() if latest_run.finished_at else None,
            "records_found": latest_run.records_found,
            "records_saved": latest_run.records_saved,
        }

    extraction_success_rate = 0.0
    if total_documents > 0:
        extraction_success_rate = round(
            (total_documents_with_text / total_documents) * 100, 2
        )

    return {
        "total_documents": total_documents,
        "total_raw_files_preserved": total_raw_files_preserved,
        "total_documents_with_text": total_documents_with_text,
        "total_duplicates_skipped": 0,
        "duplicate_tracking_note": "Duplicate count not fully tracked yet; dedupe currently uses canonical_key/content_hash.",
        "total_failed_documents": 0,
        "failed_documents_note": "Failed document count not derivable from current schema; ingestion errors tracked per run.",
        "total_ingestion_runs": total_ingestion_runs,
        "latest_ingestion_run": latest_ingestion_run,
        "extraction_success_rate": extraction_success_rate,
        "qa_needed_count": 0,
    }