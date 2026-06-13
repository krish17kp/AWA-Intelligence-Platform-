import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.coverage_snapshot import CoverageSnapshot
from app.models.document_text_block import DocumentTextBlock
from app.models.ingestion_event import IngestionEvent
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.ingestion.aphis_adapter import (
    discover_enforcement_actions,
    discover_inspection_reports,
    generate_hash_id,
    ingest_enforcement_actions,
    ingest_inspection_reports,
    normalize_pdf_url,
    parse_aphis_date,
    _record_title,
)
from app.services.ingestion.run_service import (
    run_ecfr_ingestion,
    run_federal_register_ingestion,
)
from app.services.hashing_service import sha256_bytes
from app.services.pdf_download_service import download_pdf_bytes
from app.services.storage_service import save_raw_bytes
from app.services.extraction_service import extract_text_blocks

logger = logging.getLogger(__name__)

SUPPORTED_SOURCES = [
    "aphis_inspections",
    "aphis_enforcement",
    "federal_register",
    "ecfr",
]

SOURCE_NAME_MAP = {
    "aphis_inspections": "aphis_public_search_tool",
    "aphis_enforcement": "aphis_public_search_tool",
    "federal_register": "federal_register",
    "ecfr": "ecfr",
}


def _create_event(
    db: Session,
    run_id: int,
    event_type: str,
    message: str | None = None,
    document_id: int | None = None,
    payload: dict[str, Any] | None = None,
) -> IngestionEvent:
    event = IngestionEvent(
        run_id=run_id,
        event_type=event_type,
        message=message,
        document_id=document_id,
        payload=payload,
    )
    db.add(event)
    db.commit()
    return event


def _update_extraction_status_for_existing(db: Session) -> None:
    doc_ids_with_text = set(
        row[0]
        for row in db.query(DocumentTextBlock.source_document_id).distinct().all()
    )
    for doc_id in doc_ids_with_text:
        doc = db.query(SourceDocument).filter(SourceDocument.id == doc_id).first()
        if doc and doc.extraction_status == "pending":
            doc.extraction_status = "extracted"
    db.commit()


def run_backfill(
    db: Session,
    source: str,
    start_date: str,
    end_date: str,
    max_pages: int = 2,
    page_size: int = 50,
    dry_run: bool = True,
    force_refresh: bool = False,
) -> dict[str, Any]:
    if source not in SUPPORTED_SOURCES:
        return {
            "error": f"Unsupported source '{source}'. Supported sources: {', '.join(SUPPORTED_SOURCES)}",
        }

    now = datetime.now(timezone.utc)
    parsed_start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc) if start_date else None
    parsed_end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc) if end_date else None

    ingestion_run = IngestionRun(
        source_name=SOURCE_NAME_MAP.get(source, source),
        run_status="running",
        run_type="backfill",
        started_at=now,
        date_range_start=parsed_start,
        date_range_end=parsed_end,
        records_found=0,
        records_saved=0,
        new_documents=0,
        duplicates_skipped=0,
        failed_documents=0,
    )
    db.add(ingestion_run)
    db.commit()
    db.refresh(ingestion_run)
    run_id = ingestion_run.id

    _create_event(db, run_id, "run_started", f"Backfill started for {source}")

    try:
        records_found = 0
        new_docs = 0
        duplicates = 0
        failed = 0
        records_preserved = 0
        records_extracted = 0
        errors_list: list[str] = []

        if source == "aphis_inspections":
            discovered = discover_inspection_reports(
                state_code="TX",
                max_pages=max_pages,
                max_documents=page_size,
                headless=True,
            )
            records_found = len(discovered)
            ingestion_run.records_found = records_found
            db.commit()

            for record in discovered:
                raw_link = str(record.get("reportLink") or "").strip()
                source_url = normalize_pdf_url(raw_link)
                source_id = generate_hash_id(source_url)
                canonical_key = f"aphis:inspection_report:{source_id}"

                existing = (
                    db.query(SourceDocument)
                    .filter(SourceDocument.canonical_key == canonical_key)
                    .first()
                )
                if existing and not force_refresh:
                    duplicates += 1
                    _create_event(db, run_id, "duplicate_skipped", f"Skipped duplicate inspection report", payload={"canonical_key": canonical_key})
                    continue

                if dry_run:
                    continue

                try:
                    content = download_pdf_bytes(source_url)
                except RuntimeError as e:
                    failed += 1
                    errors_list.append(f"PDF download failed for {source_url}: {e}")
                    _create_event(db, run_id, "document_failed", f"Download failed: {source_url}", payload={"error": str(e)})
                    continue

                content_hash = sha256_bytes(content)
                document_date = parse_aphis_date(record.get("inspectionDate"))
                storage_path = save_raw_bytes(
                    source_name=SOURCE_NAME_MAP[source],
                    filename=f"{source_id}_{content_hash[:12]}.pdf",
                    content=content,
                )
                records_preserved += 1

                _create_event(db, run_id, "raw_preserved", f"Raw file saved for {source_url}", payload={"storage_path": storage_path})

                doc_entry = SourceDocument(
                    source_name=SOURCE_NAME_MAP[source],
                    source_type="awa_inspection_report",
                    source_url=source_url,
                    document_title=_record_title(record, document_date),
                    document_date=document_date,
                    retrieved_at=datetime.now(timezone.utc),
                    content_hash=content_hash,
                    storage_path=storage_path,
                    mime_type="application/pdf",
                    file_size_bytes=len(content),
                    canonical_key=canonical_key,
                    extraction_status="pending",
                    raw_metadata_json={**record, "record_type": "inspection_report", "collection_method": "backfill"},
                )
                db.add(doc_entry)
                db.commit()
                db.refresh(doc_entry)
                new_docs += 1

                _create_event(db, run_id, "document_seen", f"New document saved id={doc_entry.id}", document_id=doc_entry.id, payload={"canonical_key": canonical_key})

                blocks = extract_text_blocks(
                    db,
                    source_document_id=doc_entry.id,
                    mime_type="application/pdf",
                    storage_path=storage_path,
                    fallback_url=source_url,
                )
                if blocks:
                    records_extracted += 1
                    doc_entry.extraction_status = "extracted"
                    db.commit()
                    _create_event(db, run_id, "text_extracted", f"Text extracted for doc {doc_entry.id}", document_id=doc_entry.id, payload={"block_count": len(blocks)})

        elif source == "aphis_enforcement":
            discovered = discover_enforcement_actions(
                max_pages=max_pages,
                headless=True,
            )
            if page_size > 0:
                discovered = discovered[:page_size]
            records_found = len(discovered)
            ingestion_run.records_found = records_found
            db.commit()

            for record in discovered:
                source_url = record["reportLink"]
                source_id = generate_hash_id(source_url)
                canonical_key = f"aphis:enforcement_action:{source_id}"

                existing = (
                    db.query(SourceDocument)
                    .filter(SourceDocument.canonical_key == canonical_key)
                    .first()
                )
                if existing and not force_refresh:
                    duplicates += 1
                    _create_event(db, run_id, "duplicate_skipped", f"Skipped duplicate enforcement action", payload={"canonical_key": canonical_key})
                    continue

                if dry_run:
                    continue

                try:
                    content = download_pdf_bytes(source_url)
                except RuntimeError as e:
                    failed += 1
                    errors_list.append(f"PDF download failed for {source_url}: {e}")
                    _create_event(db, run_id, "document_failed", f"Download failed: {source_url}", payload={"error": str(e)})
                    continue

                content_hash = sha256_bytes(content)
                document_date = parse_aphis_date(record.get("action_date"))
                title = "APHIS enforcement action"
                if record.get("dba"):
                    title += f" - {record['dba']}"
                if record.get("action_type"):
                    title += f" - {record['action_type']}"

                storage_path = save_raw_bytes(
                    source_name=SOURCE_NAME_MAP[source],
                    filename=f"enforcement_{source_id}_{content_hash[:12]}.pdf",
                    content=content,
                )
                records_preserved += 1

                _create_event(db, run_id, "raw_preserved", f"Raw file saved for {source_url}", payload={"storage_path": storage_path})

                doc_entry = SourceDocument(
                    source_name=SOURCE_NAME_MAP[source],
                    source_type="awa_enforcement_action",
                    source_url=source_url,
                    document_title=title,
                    document_date=document_date,
                    retrieved_at=datetime.now(timezone.utc),
                    content_hash=content_hash,
                    storage_path=storage_path,
                    mime_type="application/pdf",
                    file_size_bytes=len(content),
                    canonical_key=canonical_key,
                    extraction_status="pending",
                    raw_metadata_json={**record, "record_type": "enforcement_action", "collection_method": "backfill"},
                )
                db.add(doc_entry)
                db.commit()
                db.refresh(doc_entry)
                new_docs += 1

                _create_event(db, run_id, "document_seen", f"New document saved id={doc_entry.id}", document_id=doc_entry.id, payload={"canonical_key": canonical_key})

                blocks = extract_text_blocks(
                    db,
                    source_document_id=doc_entry.id,
                    mime_type="application/pdf",
                    storage_path=storage_path,
                    fallback_url=source_url,
                )
                if blocks:
                    records_extracted += 1
                    doc_entry.extraction_status = "extracted"
                    db.commit()
                    _create_event(db, run_id, "text_extracted", f"Text extracted for doc {doc_entry.id}", document_id=doc_entry.id, payload={"block_count": len(blocks)})

        elif source == "federal_register" or source == "ecfr":
            if dry_run:
                records_found = page_size
                ingestion_run.records_found = records_found
                db.commit()
                _create_event(db, run_id, "listing_fetched", f"Dry run: would fetch up to {page_size} records from {source}")
            else:
                _create_event(db, run_id, "listing_fetched", f"Running {source} ingestion via existing adapter")
                try:
                    if source == "federal_register":
                        result = run_federal_register_ingestion(db, per_page=page_size)
                    else:
                        result = run_ecfr_ingestion(db)

                    records_found = result.get("records_found", 0)
                    new_docs = result.get("records_saved", 0)
                    duplicates = result.get("duplicates_skipped", 0)
                    records_preserved = new_docs
                    records_extracted = new_docs

                    _create_event(db, run_id, "listing_fetched", f"Fetched {records_found} records from {source}")
                except Exception as e:
                    db.rollback()
                    raise

        if not dry_run:
            ingestion_run.run_status = "completed"
            ingestion_run.finished_at = datetime.now(timezone.utc)
            ingestion_run.new_documents = new_docs
            ingestion_run.duplicates_skipped = duplicates
            ingestion_run.failed_documents = failed
            db.commit()

            _create_event(db, run_id, "run_completed", f"Backfill completed for {source}")

            coverage_snapshot = CoverageSnapshot(
                source=SOURCE_NAME_MAP.get(source, source),
                source_type=source,
                date_range_start=parsed_start,
                date_range_end=parsed_end,
                records_found=records_found,
                records_preserved=records_preserved,
                records_extracted=records_extracted,
                duplicates_skipped=duplicates,
                failed_documents=failed,
                status="partial",
                notes=f"Backfill run {run_id}: {new_docs} new, {duplicates} duplicates, {failed} failed",
            )
            db.add(coverage_snapshot)
            db.commit()

            _update_extraction_status_for_existing(db)
        else:
            ingestion_run.run_status = "dry_run"
            ingestion_run.finished_at = datetime.now(timezone.utc)
            ingestion_run.new_documents = 0
            ingestion_run.duplicates_skipped = 0
            ingestion_run.failed_documents = 0
            db.commit()

            _create_event(db, run_id, "run_completed", f"Dry run completed for {source}")

        return {
            "run_id": run_id,
            "source": source,
            "status": ingestion_run.run_status,
            "dry_run": dry_run,
            "records_found": records_found,
            "new_documents": new_docs,
            "duplicates_skipped": duplicates,
            "failed_documents": failed,
            "records_preserved": records_preserved,
            "records_extracted": records_extracted,
            "errors": errors_list,
            "warning": "This does not mean full historical coverage is complete. Coverage is partial until source/date coverage is validated.",
        }

    except Exception as error:
        db.rollback()
        ingestion_run = db.get(IngestionRun, run_id)
        if ingestion_run is not None:
            ingestion_run.run_status = "failed"
            ingestion_run.finished_at = datetime.now(timezone.utc)
            ingestion_run.error_message = str(error)
            db.commit()
            _create_event(db, run_id, "run_failed", f"Backfill failed: {error}", payload={"error": str(error)})

        return {
            "run_id": run_id,
            "source": source,
            "status": "failed",
            "dry_run": dry_run,
            "records_found": 0,
            "new_documents": 0,
            "duplicates_skipped": 0,
            "failed_documents": 0,
            "records_preserved": 0,
            "records_extracted": 0,
            "errors": [str(error)],
            "warning": "This does not mean full historical coverage is complete. Coverage is partial until source/date coverage is validated.",
        }