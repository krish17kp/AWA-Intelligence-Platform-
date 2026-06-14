from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.coverage_snapshot import CoverageSnapshot
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.backfill_service import FULL_COVERAGE_MESSAGE, KNOWN_LIMITATIONS

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _run_response(run: IngestionRun | None) -> dict | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "source": run.source_name,
        "status": run.run_status,
        "run_type": run.run_type,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.finished_at.isoformat() if run.finished_at else None,
        "records_found": run.records_found,
        "records_saved": run.records_saved,
        "new_documents": run.new_documents or 0,
        "duplicates_skipped": run.duplicates_skipped or 0,
        "failed_documents": run.failed_documents or 0,
    }


@router.get("/coverage")
def get_coverage(db: Session = Depends(get_db)):
    total_documents = db.query(SourceDocument).count()
    snapshot_count = db.query(CoverageSnapshot).count()

    document_source_rows = (
        db.query(SourceDocument.source_name, func.count(SourceDocument.id))
        .group_by(SourceDocument.source_name)
        .all()
    )
    snapshot_source_rows = (
        db.query(
            CoverageSnapshot.source_type,
            func.sum(CoverageSnapshot.records_found),
        )
        .group_by(CoverageSnapshot.source_type)
        .all()
    )
    total_records_by_source = {
        source: count
        for source, count in document_source_rows
        if source
    }
    snapshot_physical_sources = {
        source
        for (source,) in db.query(CoverageSnapshot.source)
        .distinct()
        .all()
        if source
    }
    for physical_source in snapshot_physical_sources:
        total_records_by_source.pop(physical_source, None)
    for source, count in snapshot_source_rows:
        if source:
            total_records_by_source[source] = int(count or 0)

    source_names = {
        source
        for source, _ in document_source_rows
        if source and source not in snapshot_physical_sources
    } | {
        source for source, _ in snapshot_source_rows if source
    }
    sources_attempted = sorted(source_names)

    state_rows = (
        db.query(
            CoverageSnapshot.state_code,
            func.sum(CoverageSnapshot.records_found),
        )
        .filter(CoverageSnapshot.state_code.isnot(None))
        .group_by(CoverageSnapshot.state_code)
        .order_by(CoverageSnapshot.state_code)
        .all()
    )
    states_attempted = [state for state, _ in state_rows]
    total_records_by_state = {
        state: int(count or 0) for state, count in state_rows
    }

    range_rows = (
        db.query(
            CoverageSnapshot.source_type,
            CoverageSnapshot.state_code,
            CoverageSnapshot.date_range_start,
            CoverageSnapshot.date_range_end,
        )
        .filter(
            CoverageSnapshot.date_range_start.isnot(None),
            CoverageSnapshot.date_range_end.isnot(None),
        )
        .order_by(CoverageSnapshot.created_at.desc())
        .all()
    )
    seen_ranges: set[tuple] = set()
    date_ranges_attempted = []
    for source, state, start, end in range_rows:
        key = (source, state, start, end)
        if key in seen_ranges:
            continue
        seen_ranges.add(key)
        date_ranges_attempted.append(
            {
                "source": source,
                "state_code": state,
                "start": start.isoformat() if start else None,
                "end": end.isoformat() if end else None,
            }
        )

    last_successful_run = (
        db.query(IngestionRun)
        .filter(
            IngestionRun.run_status.in_(
                ("completed", "success", "partial_success")
            )
        )
        .order_by(IngestionRun.finished_at.desc(), IngestionRun.created_at.desc())
        .first()
    )

    snapshots = (
        db.query(CoverageSnapshot)
        .order_by(CoverageSnapshot.created_at.desc())
        .limit(20)
        .all()
    )
    latest_coverage_snapshots = [
        {
            "id": snapshot.id,
            "source": snapshot.source,
            "source_type": snapshot.source_type,
            "state_code": snapshot.state_code,
            "date_range_start": (
                snapshot.date_range_start.isoformat()
                if snapshot.date_range_start
                else None
            ),
            "date_range_end": (
                snapshot.date_range_end.isoformat()
                if snapshot.date_range_end
                else None
            ),
            "filters_json": snapshot.filters_json,
            "records_found": snapshot.records_found,
            "records_preserved": snapshot.records_preserved,
            "records_extracted": snapshot.records_extracted,
            "duplicates_skipped": snapshot.duplicates_skipped,
            "failed_documents": snapshot.failed_documents,
            "status": snapshot.status,
            "notes": snapshot.notes,
            "created_at": (
                snapshot.created_at.isoformat() if snapshot.created_at else None
            ),
        }
        for snapshot in snapshots
    ]

    historical_backfill_status = (
        "not_started"
        if total_documents == 0 and snapshot_count == 0
        else "partial"
    )

    return {
        "historical_backfill_status": historical_backfill_status,
        "message": FULL_COVERAGE_MESSAGE,
        "sources_attempted": sources_attempted,
        "states_attempted": states_attempted,
        "date_ranges_attempted": date_ranges_attempted,
        "total_records_by_source": total_records_by_source,
        "total_records_by_state": total_records_by_state,
        "latest_coverage_snapshots": latest_coverage_snapshots[:5],
        "last_successful_run": _run_response(last_successful_run),
        "known_limitations": KNOWN_LIMITATIONS,
    }
