from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.coverage_snapshot import CoverageSnapshot
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

    has_any_documents = total_documents > 0

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
            "run_type": last_run.run_type,
            "started_at": last_run.started_at.isoformat() if last_run.started_at else None,
            "completed_at": last_run.finished_at.isoformat() if last_run.finished_at else None,
            "records_found": last_run.records_found,
            "records_saved": last_run.records_saved,
            "new_documents": getattr(last_run, 'new_documents', 0) or 0,
            "duplicates_skipped": getattr(last_run, 'duplicates_skipped', 0) or 0,
            "failed_documents": getattr(last_run, 'failed_documents', 0) or 0,
        }

    coverage_snapshots = []
    try:
        snapshots = (
            db.query(CoverageSnapshot)
            .order_by(CoverageSnapshot.created_at.desc())
            .limit(20)
            .all()
        )
        coverage_snapshots = [
            {
                "id": s.id,
                "source": s.source,
                "source_type": s.source_type,
                "date_range_start": s.date_range_start.isoformat() if s.date_range_start else None,
                "date_range_end": s.date_range_end.isoformat() if s.date_range_end else None,
                "records_found": s.records_found,
                "records_preserved": s.records_preserved,
                "records_extracted": s.records_extracted,
                "duplicates_skipped": s.duplicates_skipped,
                "failed_documents": s.failed_documents,
                "status": s.status,
                "notes": s.notes,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snapshots
        ]
    except Exception:
        coverage_snapshots = []

    historical_backfill_status = "not_started"
    if has_any_documents or coverage_snapshots:
        historical_backfill_status = "partial"

    known_limitations = [
        "Full historical APHIS coverage is not complete yet.",
        "Coverage is partial until source/date coverage is validated against run logs.",
        "Only APHIS inspections, APHIS enforcement, Federal Register, and eCFR sources are currently supported.",
        "Existing pre-migration records may have canonical_key=NULL.",
    ]

    return {
        "historical_backfill_status": historical_backfill_status,
        "message": "Full historical APHIS coverage is not complete yet. Current data reflects completed backfill runs and coverage snapshots only.",
        "sources_attempted": sources_attempted,
        "date_ranges_attempted": date_ranges_attempted,
        "total_records_by_source": total_records_by_source,
        "latest_coverage_snapshots": coverage_snapshots[:5],
        "last_successful_run": last_successful_run,
        "known_limitations": known_limitations,
    }