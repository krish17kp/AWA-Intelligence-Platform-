from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.extraction_service import extract_text_blocks
from app.services.ingestion.ecfr_adapter import fetch_ecfr_title_9_sample
from app.services.ingestion.federal_register_adapter import (
    fetch_federal_register_animal_welfare_records,
)


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _start_run(db: Session, source_name: str) -> IngestionRun:
    run = IngestionRun(
        source_name=source_name,
        run_status="running",
        started_at=datetime.now(timezone.utc),
        records_found=0,
        records_saved=0,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _finish_run(
    db: Session,
    run: IngestionRun,
    *,
    status: str,
    records_found: int,
    records_saved: int,
    error_message: str | None = None,
) -> None:
    run.run_status = status
    run.finished_at = datetime.now(timezone.utc)
    run.records_found = records_found
    run.records_saved = records_saved
    run.error_message = error_message
    db.commit()


def _document_exists(
    db: Session,
    *,
    source_name: str,
    source_url: str,
    content_hash: str,
) -> bool:
    return (
        db.query(SourceDocument.id)
        .filter(
            SourceDocument.source_name == source_name,
            SourceDocument.source_url == source_url,
            SourceDocument.content_hash == content_hash,
        )
        .first()
        is not None
    )


def run_ecfr_ingestion(db: Session) -> dict[str, Any]:
    run = _start_run(db, "ecfr")
    run_id = run.id
    try:
        result = fetch_ecfr_title_9_sample()
        saved = 0
        duplicates_skipped = 0
        changed_records = 0

        canonical_key = f"ecfr:title-9:2024-01-01"
        existing = (
            db.query(SourceDocument)
            .filter(
                SourceDocument.source_name == "ecfr",
                SourceDocument.canonical_key == canonical_key,
            )
            .first()
        )
        if existing:
            if existing.content_hash == result["content_hash"]:
                duplicates_skipped = 1
            else:
                changed_records = 1
        else:
            doc = SourceDocument(
                source_name="ecfr",
                source_type="regulatory_citation_mapping",
                source_url=result["source_url"],
                document_title="eCFR Title 9 regulatory text",
                document_date=None,
                retrieved_at=result["retrieved_at"],
                content_hash=result["content_hash"],
                storage_path=result["storage_path"],
                mime_type="application/xml",
                file_size_bytes=result["file_size_bytes"],
                canonical_key=canonical_key,
                raw_metadata_json={
                    "source": "eCFR API",
                    "title": "Title 9",
                    "purpose": "CFR citation mapping for AWA violations",
                },
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            extract_text_blocks(
                db,
                source_document_id=doc.id,
                mime_type="application/xml",
                storage_path=result["storage_path"],
                fallback_url=result["source_url"],
            )
            saved = 1

        _finish_run(
            db,
            run,
            status="success",
            records_found=1,
            records_saved=saved,
        )
        return {
            "source_name": "ecfr",
            "source_type": "regulatory_citation_mapping",
            "source_subtype": "regulatory_citation_mapping",
            "status": "success",
            "records_found": 1,
            "records_saved": saved,
            "duplicates_skipped": duplicates_skipped,
            "changed_records": changed_records,
            "errors": [],
            "ingestion_run_id": run_id,
        }
    except Exception as error:
        db.rollback()
        run = db.get(IngestionRun, run_id)
        if run is not None:
            _finish_run(
                db,
                run,
                status="failed",
                records_found=0,
                records_saved=0,
                error_message=str(error),
            )
        raise


def run_federal_register_ingestion(
    db: Session,
    per_page: int = 5,
) -> dict[str, Any]:
    run = _start_run(db, "federal_register")
    run_id = run.id
    try:
        result = fetch_federal_register_animal_welfare_records(per_page=per_page)
        records = result["raw_json"].get("results", [])
        saved = 0
        duplicates_skipped = 0

        for record in records:
            source_url = record.get("html_url") or record.get("pdf_url")
            if not source_url:
                continue

            doc_number = record.get("document_number", "")
            canonical_key = f"federal_register:{doc_number}" if doc_number else f"federal_register:{source_url}"

            existing = (
                db.query(SourceDocument)
                .filter(SourceDocument.canonical_key == canonical_key)
                .first()
            )
            if existing:
                duplicates_skipped += 1
                continue

            doc = SourceDocument(
                source_name="federal_register",
                source_type=record.get("type") or "federal_register_document",
                source_url=source_url,
                document_title=record.get("title"),
                document_date=_parse_date(record.get("publication_date")),
                retrieved_at=result["retrieved_at"],
                content_hash=result["content_hash"],
                storage_path=result["storage_path"],
                mime_type="application/json",
                file_size_bytes=result["file_size_bytes"],
                canonical_key=canonical_key,
                raw_metadata_json=record,
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            extract_text_blocks(
                db,
                source_document_id=doc.id,
                mime_type="application/json",
                storage_path=result["storage_path"],
                fallback_url=source_url,
            )
            saved += 1

        db.commit()
        _finish_run(
            db,
            run,
            status="success",
            records_found=len(records),
            records_saved=saved,
        )
        return {
            "source_name": "federal_register",
            "source_type": "regulatory_records",
            "source_subtype": "regulatory_records",
            "status": "success",
            "records_found": len(records),
            "records_saved": saved,
            "duplicates_skipped": duplicates_skipped,
            "changed_records": 0,
            "errors": [],
            "ingestion_run_id": run_id,
        }
    except Exception as error:
        db.rollback()
        run = db.get(IngestionRun, run_id)
        if run is not None:
            _finish_run(
                db,
                run,
                status="failed",
                records_found=0,
                records_saved=0,
                error_message=str(error),
            )
        raise
