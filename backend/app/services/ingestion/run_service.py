import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.hashing_service import sha256_bytes
from app.services.ingestion.ecfr_adapter import fetch_ecfr_title_9_sample
from app.services.ingestion.federal_register_adapter import (
    fetch_federal_register_animal_welfare_records,
)
from app.services.storage_service import save_raw_bytes


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
        if not _document_exists(
            db,
            source_name="ecfr",
            source_url=result["source_url"],
            content_hash=result["content_hash"],
        ):
            db.add(
                SourceDocument(
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
                    raw_metadata_json={
                        "source": "eCFR API",
                        "title": "Title 9",
                        "purpose": "CFR citation mapping for AWA violations",
                    },
                )
            )
            db.commit()
            saved = 1

        _finish_run(
            db,
            run,
            status="success",
            records_found=1,
            records_saved=saved,
        )
        return {
            "ingestion_run_id": run_id,
            "run_status": "success",
            "records_found": 1,
            "records_saved": saved,
            "duplicates_skipped": 1 - saved,
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

        for record in records:
            source_url = record.get("html_url") or record.get("pdf_url")
            if not source_url or _document_exists(
                db,
                source_name="federal_register",
                source_url=source_url,
                content_hash=result["content_hash"],
            ):
                continue

            db.add(
                SourceDocument(
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
                    raw_metadata_json=record,
                )
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
            "ingestion_run_id": run_id,
            "run_status": "success",
            "records_found": len(records),
            "records_saved": saved,
            "duplicates_skipped": len(records) - saved,
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


def run_supplied_records_ingestion(
    db: Session,
    *,
    source_name: str,
    source_type: str,
    source_url: str,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    run = _start_run(db, source_name)
    run_id = run.id
    try:
        if not records:
            _finish_run(
                db,
                run,
                status="success",
                records_found=0,
                records_saved=0,
            )
            return {
                "ingestion_run_id": run_id,
                "run_status": "success",
                "records_found": 0,
                "records_saved": 0,
                "duplicates_skipped": 0,
            }

        retrieved_at = datetime.now(timezone.utc)
        raw_content = json.dumps(
            records,
            ensure_ascii=True,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        content_hash = sha256_bytes(raw_content)
        timestamp = retrieved_at.strftime("%Y%m%d_%H%M%S")
        storage_path = save_raw_bytes(
            source_name=source_name,
            filename=f"{source_type}_{timestamp}_{content_hash[:12]}.json",
            content=raw_content,
        )
        saved = 0

        for index, record in enumerate(records):
            record_url = (
                record.get("source_url")
                or record.get("url")
                or record.get("reportLink")
                or f"{source_url}#record-{index + 1}"
            )
            if _document_exists(
                db,
                source_name=source_name,
                source_url=record_url,
                content_hash=content_hash,
            ):
                continue

            db.add(
                SourceDocument(
                    source_name=source_name,
                    source_type=source_type,
                    source_url=record_url,
                    document_title=record.get("title")
                    or record.get("name")
                    or record.get("document_title"),
                    document_date=_parse_date(
                        record.get("document_date")
                        or record.get("date")
                        or record.get("publication_date")
                    ),
                    retrieved_at=retrieved_at,
                    content_hash=content_hash,
                    storage_path=storage_path,
                    mime_type="application/json",
                    file_size_bytes=len(raw_content),
                    raw_metadata_json=record,
                )
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
            "ingestion_run_id": run_id,
            "run_status": "success",
            "records_found": len(records),
            "records_saved": saved,
            "duplicates_skipped": len(records) - saved,
        }
    except Exception as error:
        db.rollback()
        run = db.get(IngestionRun, run_id)
        if run is not None:
            _finish_run(
                db,
                run,
                status="failed",
                records_found=len(records),
                records_saved=0,
                error_message=str(error),
            )
        raise
