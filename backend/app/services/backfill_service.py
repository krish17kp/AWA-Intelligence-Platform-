import logging
from datetime import datetime, time, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.coverage_snapshot import CoverageSnapshot
from app.models.document_text_block import DocumentTextBlock
from app.models.ingestion_event import IngestionEvent
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.extraction_service import extract_text_blocks
from app.services.hashing_service import sha256_bytes
from app.services.ingestion.aphis_adapter import (
    _record_title,
    discover_enforcement_actions,
    discover_inspection_reports,
    generate_hash_id,
    normalize_pdf_url,
    parse_aphis_date,
)
from app.services.ingestion.run_service import (
    run_ecfr_ingestion,
    run_federal_register_ingestion,
)
from app.services.pdf_download_service import download_pdf_bytes
from app.services.storage_service import save_raw_bytes

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

DEFAULT_APHIS_STATE = "TX"
US_STATE_CODES = (
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
)

FULL_COVERAGE_MESSAGE = (
    "Full historical APHIS coverage is not complete unless all required "
    "source/date/state ranges have completed coverage snapshots."
)

KNOWN_LIMITATIONS = [
    FULL_COVERAGE_MESSAGE,
    "APHIS inspection date filtering is applied to records returned by the public search tool; the upstream listing may have additional records outside the fetched page cap.",
    "eCFR and Federal Register backfills delegate to existing adapters with their own retrieval limits.",
    "Railway S3 endpoint configuration and signed raw-document URLs remain unverified.",
]


def build_backfill_warning(
    *,
    source: str,
    state_code: str | None,
    include_all_states: bool,
    plan_only: bool = False,
) -> str:
    if (
        source == "aphis_inspections"
        and not state_code
        and not include_all_states
    ):
        return (
            "APHIS backfill defaulted to state_code=TX because no state_code "
            "or include_all_states option was provided."
        )
    if plan_only:
        return (
            "This endpoint only creates a plan. Full historical backfill is "
            "not complete until run logs and coverage records prove it."
        )
    return FULL_COVERAGE_MESSAGE


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
    doc_ids_with_text = {
        row[0]
        for row in db.query(DocumentTextBlock.source_document_id).distinct().all()
    }
    for doc_id in doc_ids_with_text:
        doc = db.query(SourceDocument).filter(SourceDocument.id == doc_id).first()
        if doc and doc.extraction_status == "pending":
            doc.extraction_status = "extracted"
    db.commit()


def _range_datetime(value: str, *, end: bool = False) -> datetime:
    parsed = datetime.fromisoformat(value).date()
    return datetime.combine(
        parsed,
        time.max if end else time.min,
        tzinfo=timezone.utc,
    )


def _empty_counts() -> dict[str, Any]:
    return {
        "records_found": 0,
        "new_documents": 0,
        "duplicates_skipped": 0,
        "failed_documents": 0,
        "records_preserved": 0,
        "records_extracted": 0,
        "errors": [],
    }


def _add_counts(total: dict[str, Any], current: dict[str, Any]) -> None:
    for key in (
        "records_found",
        "new_documents",
        "duplicates_skipped",
        "failed_documents",
        "records_preserved",
        "records_extracted",
    ):
        total[key] += current[key]
    total["errors"].extend(current["errors"])


def _record_matches_filters(
    record: dict[str, Any],
    *,
    start_at: datetime,
    end_at: datetime,
    date_keys: tuple[str, ...],
    facility_name: str | None,
    customer_number: str | None,
) -> bool:
    document_date = next(
        (
            parse_aphis_date(record.get(key))
            for key in date_keys
            if record.get(key)
        ),
        None,
    )
    if document_date and not (start_at <= document_date <= end_at):
        return False

    if facility_name:
        requested_name = facility_name.strip().casefold()
        facility_values = (
            record.get("siteName"),
            record.get("legalName"),
            record.get("customerName"),
            record.get("accountName"),
            record.get("dba"),
        )
        if not any(
            requested_name in str(value).casefold()
            for value in facility_values
            if value
        ):
            return False

    if customer_number:
        requested_customer = customer_number.strip().casefold()
        customer_values = (
            record.get("customerNumber"),
            record.get("customer_number"),
            record.get("customerNo"),
            record.get("customerId"),
        )
        if not any(
            requested_customer == str(value).strip().casefold()
            for value in customer_values
            if value
        ):
            return False

    return True


def _find_duplicate(
    db: Session,
    *,
    canonical_key: str | None = None,
    content_hash: str | None = None,
) -> tuple[SourceDocument | None, str | None]:
    if canonical_key:
        existing = (
            db.query(SourceDocument)
            .filter(SourceDocument.canonical_key == canonical_key)
            .first()
        )
        if existing:
            return existing, "canonical_key"
    if content_hash:
        existing = (
            db.query(SourceDocument)
            .filter(SourceDocument.content_hash == content_hash)
            .first()
        )
        if existing:
            return existing, "content_hash"
    return None, None


def _record_duplicate_event(
    db: Session,
    *,
    run_id: int,
    existing: SourceDocument,
    matched_on: str,
    canonical_key: str,
    state_code: str | None,
) -> None:
    _create_event(
        db,
        run_id,
        "duplicate_skipped",
        f"Skipped duplicate document matching {matched_on}",
        document_id=existing.id,
        payload={
            "duplicate_of": existing.id,
            "matched_on": matched_on,
            "canonical_key": canonical_key,
            "state_code": state_code,
        },
    )


def _process_aphis_inspections(
    db: Session,
    *,
    run_id: int,
    state_code: str,
    start_at: datetime,
    end_at: datetime,
    max_pages: int,
    page_size: int,
    dry_run: bool,
    force_refresh: bool,
    license_type: str | None,
    facility_name: str | None,
    customer_number: str | None,
    filters: dict[str, Any],
) -> dict[str, Any]:
    counts = _empty_counts()
    discovered = discover_inspection_reports(
        state_code=state_code,
        license_type=license_type,
        max_pages=max_pages,
        max_documents=0,
        headless=True,
    )
    filtered = [
        record
        for record in discovered
        if _record_matches_filters(
            record,
            start_at=start_at,
            end_at=end_at,
            date_keys=("inspectionDate",),
            facility_name=facility_name,
            customer_number=customer_number,
        )
    ][:page_size]
    counts["records_found"] = len(filtered)
    _create_event(
        db,
        run_id,
        "listing_fetched",
        f"Fetched {len(filtered)} APHIS inspection records for {state_code}",
        payload={
            "state_code": state_code,
            "records_returned": len(discovered),
            "records_after_filters": len(filtered),
            "filters": filters,
        },
    )

    for record in filtered:
        raw_link = str(record.get("reportLink") or "").strip()
        source_url = normalize_pdf_url(raw_link)
        source_id = generate_hash_id(source_url)
        canonical_key = f"aphis:inspection_report:{source_id}"
        canonical_match, matched_on = _find_duplicate(
            db,
            canonical_key=canonical_key,
        )
        if canonical_match and not force_refresh:
            counts["duplicates_skipped"] += 1
            _record_duplicate_event(
                db,
                run_id=run_id,
                existing=canonical_match,
                matched_on=matched_on or "canonical_key",
                canonical_key=canonical_key,
                state_code=state_code,
            )
            continue

        if dry_run:
            continue

        try:
            content = download_pdf_bytes(source_url)
        except RuntimeError as error:
            counts["failed_documents"] += 1
            counts["errors"].append(f"PDF download failed for {source_url}: {error}")
            _create_event(
                db,
                run_id,
                "document_failed",
                f"Download failed: {source_url}",
                payload={"error": str(error), "state_code": state_code},
            )
            continue

        content_hash = sha256_bytes(content)
        content_match, content_matched_on = _find_duplicate(
            db,
            content_hash=content_hash,
        )
        if content_match and not force_refresh:
            counts["duplicates_skipped"] += 1
            _record_duplicate_event(
                db,
                run_id=run_id,
                existing=content_match,
                matched_on=content_matched_on or "content_hash",
                canonical_key=canonical_key,
                state_code=state_code,
            )
            continue

        duplicate_of = (
            canonical_match.id
            if canonical_match
            else content_match.id if content_match else None
        )
        document_date = parse_aphis_date(record.get("inspectionDate"))
        storage_path = save_raw_bytes(
            source_name=SOURCE_NAME_MAP["aphis_inspections"],
            filename=f"{source_id}_{content_hash[:12]}.pdf",
            content=content,
        )
        counts["records_preserved"] += 1
        _create_event(
            db,
            run_id,
            "raw_preserved",
            f"Raw file saved for {source_url}",
            payload={"storage_path": storage_path, "state_code": state_code},
        )

        doc_entry = SourceDocument(
            source_name=SOURCE_NAME_MAP["aphis_inspections"],
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
            duplicate_of=duplicate_of,
            extraction_status="pending",
            raw_metadata_json={
                **record,
                "record_type": "inspection_report",
                "collection_method": "backfill",
                "backfill_filters": filters,
                "state_filter": state_code,
            },
        )
        db.add(doc_entry)
        db.commit()
        db.refresh(doc_entry)
        counts["new_documents"] += 1
        _create_event(
            db,
            run_id,
            "document_seen",
            f"New document saved id={doc_entry.id}",
            document_id=doc_entry.id,
            payload={
                "canonical_key": canonical_key,
                "duplicate_of": duplicate_of,
                "state_code": state_code,
            },
        )

        blocks = extract_text_blocks(
            db,
            source_document_id=doc_entry.id,
            mime_type="application/pdf",
            storage_path=storage_path,
            fallback_url=source_url,
        )
        if blocks:
            counts["records_extracted"] += 1
            doc_entry.extraction_status = "extracted"
            db.commit()
            _create_event(
                db,
                run_id,
                "text_extracted",
                f"Text extracted for doc {doc_entry.id}",
                document_id=doc_entry.id,
                payload={"block_count": len(blocks), "state_code": state_code},
            )

    return counts


def _process_aphis_enforcement(
    db: Session,
    *,
    run_id: int,
    start_at: datetime,
    end_at: datetime,
    max_pages: int,
    page_size: int,
    dry_run: bool,
    force_refresh: bool,
    license_type: str | None,
    facility_name: str | None,
    customer_number: str | None,
    filters: dict[str, Any],
) -> dict[str, Any]:
    counts = _empty_counts()
    discovered = discover_enforcement_actions(max_pages=max_pages, headless=True)
    filtered = [
        record
        for record in discovered
        if _record_matches_filters(
            record,
            start_at=start_at,
            end_at=end_at,
            date_keys=("action_date",),
            facility_name=facility_name,
            customer_number=customer_number,
        )
        and (
            not license_type
            or license_type.strip().casefold()
            in str(record.get("license_category") or "").casefold()
        )
    ][:page_size]
    counts["records_found"] = len(filtered)
    _create_event(
        db,
        run_id,
        "listing_fetched",
        f"Fetched {len(filtered)} APHIS enforcement records",
        payload={
            "records_returned": len(discovered),
            "records_after_filters": len(filtered),
            "filters": filters,
        },
    )

    for record in filtered:
        source_url = record["reportLink"]
        source_id = generate_hash_id(source_url)
        canonical_key = f"aphis:enforcement_action:{source_id}"
        canonical_match, matched_on = _find_duplicate(
            db,
            canonical_key=canonical_key,
        )
        if canonical_match and not force_refresh:
            counts["duplicates_skipped"] += 1
            _record_duplicate_event(
                db,
                run_id=run_id,
                existing=canonical_match,
                matched_on=matched_on or "canonical_key",
                canonical_key=canonical_key,
                state_code=None,
            )
            continue

        if dry_run:
            continue

        try:
            content = download_pdf_bytes(source_url)
        except RuntimeError as error:
            counts["failed_documents"] += 1
            counts["errors"].append(f"PDF download failed for {source_url}: {error}")
            _create_event(
                db,
                run_id,
                "document_failed",
                f"Download failed: {source_url}",
                payload={"error": str(error)},
            )
            continue

        content_hash = sha256_bytes(content)
        content_match, content_matched_on = _find_duplicate(
            db,
            content_hash=content_hash,
        )
        if content_match and not force_refresh:
            counts["duplicates_skipped"] += 1
            _record_duplicate_event(
                db,
                run_id=run_id,
                existing=content_match,
                matched_on=content_matched_on or "content_hash",
                canonical_key=canonical_key,
                state_code=None,
            )
            continue

        duplicate_of = (
            canonical_match.id
            if canonical_match
            else content_match.id if content_match else None
        )
        document_date = parse_aphis_date(record.get("action_date"))
        title = "APHIS enforcement action"
        if record.get("dba"):
            title += f" - {record['dba']}"
        if record.get("action_type"):
            title += f" - {record['action_type']}"

        storage_path = save_raw_bytes(
            source_name=SOURCE_NAME_MAP["aphis_enforcement"],
            filename=f"enforcement_{source_id}_{content_hash[:12]}.pdf",
            content=content,
        )
        counts["records_preserved"] += 1
        _create_event(
            db,
            run_id,
            "raw_preserved",
            f"Raw file saved for {source_url}",
            payload={"storage_path": storage_path},
        )

        doc_entry = SourceDocument(
            source_name=SOURCE_NAME_MAP["aphis_enforcement"],
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
            duplicate_of=duplicate_of,
            extraction_status="pending",
            raw_metadata_json={
                **record,
                "record_type": "enforcement_action",
                "collection_method": "backfill",
                "backfill_filters": filters,
            },
        )
        db.add(doc_entry)
        db.commit()
        db.refresh(doc_entry)
        counts["new_documents"] += 1
        _create_event(
            db,
            run_id,
            "document_seen",
            f"New document saved id={doc_entry.id}",
            document_id=doc_entry.id,
            payload={
                "canonical_key": canonical_key,
                "duplicate_of": duplicate_of,
            },
        )

        blocks = extract_text_blocks(
            db,
            source_document_id=doc_entry.id,
            mime_type="application/pdf",
            storage_path=storage_path,
            fallback_url=source_url,
        )
        if blocks:
            counts["records_extracted"] += 1
            doc_entry.extraction_status = "extracted"
            db.commit()
            _create_event(
                db,
                run_id,
                "text_extracted",
                f"Text extracted for doc {doc_entry.id}",
                document_id=doc_entry.id,
                payload={"block_count": len(blocks)},
            )

    return counts


def _process_delegated_source(
    db: Session,
    *,
    run_id: int,
    source: str,
    page_size: int,
    dry_run: bool,
) -> dict[str, Any]:
    counts = _empty_counts()
    if dry_run:
        counts["records_found"] = page_size
        _create_event(
            db,
            run_id,
            "listing_fetched",
            f"Dry run: would fetch up to {page_size} records from {source}",
        )
        return counts

    _create_event(
        db,
        run_id,
        "listing_fetched",
        f"Running {source} ingestion via existing adapter",
    )
    if source == "federal_register":
        result = run_federal_register_ingestion(db, per_page=page_size)
    else:
        result = run_ecfr_ingestion(db)
    counts["records_found"] = result.get("records_found", 0)
    counts["new_documents"] = result.get("records_saved", 0)
    counts["duplicates_skipped"] = result.get("duplicates_skipped", 0)
    counts["records_preserved"] = counts["new_documents"]
    counts["records_extracted"] = counts["new_documents"]
    return counts


def _create_coverage_snapshot(
    db: Session,
    *,
    source: str,
    state_code: str | None,
    start_at: datetime,
    end_at: datetime,
    filters: dict[str, Any],
    counts: dict[str, Any],
    status: str,
    run_id: int,
) -> int:
    snapshot = CoverageSnapshot(
        source=SOURCE_NAME_MAP.get(source, source),
        source_type=source,
        state_code=state_code,
        date_range_start=start_at,
        date_range_end=end_at,
        filters_json=filters,
        records_found=counts["records_found"],
        records_preserved=counts["records_preserved"],
        records_extracted=counts["records_extracted"],
        duplicates_skipped=counts["duplicates_skipped"],
        failed_documents=counts["failed_documents"],
        status=status,
        notes=(
            f"Backfill run {run_id}: {counts['new_documents']} new, "
            f"{counts['duplicates_skipped']} duplicates, "
            f"{counts['failed_documents']} failed"
        ),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot.id


def run_backfill(
    db: Session,
    source: str,
    start_date: str,
    end_date: str,
    max_pages: int = 2,
    page_size: int = 50,
    dry_run: bool = True,
    force_refresh: bool = False,
    state_code: str | None = None,
    license_type: str | None = None,
    facility_name: str | None = None,
    customer_number: str | None = None,
    include_all_states: bool = False,
) -> dict[str, Any]:
    if source not in SUPPORTED_SOURCES:
        return {"error": f"Unsupported source '{source}'."}

    start_at = _range_datetime(start_date)
    end_at = _range_datetime(end_date, end=True)
    effective_state = None
    if source == "aphis_inspections" and not include_all_states:
        effective_state = state_code or DEFAULT_APHIS_STATE
    states: list[str | None]
    if source == "aphis_inspections":
        states = list(US_STATE_CODES) if include_all_states else [effective_state]
    else:
        states = [None]

    filters = {
        "state_code": effective_state,
        "license_type": license_type,
        "facility_name": facility_name,
        "customer_number": customer_number,
        "include_all_states": include_all_states,
        "max_pages": max_pages,
        "page_size": page_size,
        "force_refresh": force_refresh,
    }
    now = datetime.now(timezone.utc)
    ingestion_run = IngestionRun(
        source_name=SOURCE_NAME_MAP.get(source, source),
        run_status="running",
        run_type="backfill",
        started_at=now,
        date_range_start=start_at,
        date_range_end=end_at,
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
    _create_event(
        db,
        run_id,
        "run_started",
        f"Backfill started for {source}",
        payload={"filters": filters, "states_count": len(states)},
    )

    totals = _empty_counts()
    snapshot_ids: list[int] = []
    successful_units = 0

    for current_state in states:
        unit_label = current_state or source
        if current_state:
            _create_event(
                db,
                run_id,
                "state_started",
                f"Starting APHIS backfill for {current_state}",
                payload={"state_code": current_state},
            )

        unit_filters = {**filters, "state_code": current_state}
        try:
            if source == "aphis_inspections":
                unit_counts = _process_aphis_inspections(
                    db,
                    run_id=run_id,
                    state_code=current_state or DEFAULT_APHIS_STATE,
                    start_at=start_at,
                    end_at=end_at,
                    max_pages=max_pages,
                    page_size=page_size,
                    dry_run=dry_run,
                    force_refresh=force_refresh,
                    license_type=license_type,
                    facility_name=facility_name,
                    customer_number=customer_number,
                    filters=unit_filters,
                )
            elif source == "aphis_enforcement":
                unit_counts = _process_aphis_enforcement(
                    db,
                    run_id=run_id,
                    start_at=start_at,
                    end_at=end_at,
                    max_pages=max_pages,
                    page_size=page_size,
                    dry_run=dry_run,
                    force_refresh=force_refresh,
                    license_type=license_type,
                    facility_name=facility_name,
                    customer_number=customer_number,
                    filters=unit_filters,
                )
            else:
                unit_counts = _process_delegated_source(
                    db,
                    run_id=run_id,
                    source=source,
                    page_size=page_size,
                    dry_run=dry_run,
                )

            successful_units += 1
            if current_state:
                _create_event(
                    db,
                    run_id,
                    "state_completed",
                    f"Completed APHIS backfill for {current_state}",
                    payload={
                        "state_code": current_state,
                        **{
                            key: unit_counts[key]
                            for key in (
                                "records_found",
                                "new_documents",
                                "duplicates_skipped",
                                "failed_documents",
                            )
                        },
                    },
                )
            if not dry_run:
                snapshot_ids.append(
                    _create_coverage_snapshot(
                        db,
                        source=source,
                        state_code=current_state,
                        start_at=start_at,
                        end_at=end_at,
                        filters=unit_filters,
                        counts=unit_counts,
                        status="partial",
                        run_id=run_id,
                    )
                )
            _add_counts(totals, unit_counts)
        except Exception as error:
            db.rollback()
            failed_counts = _empty_counts()
            failed_counts["failed_documents"] = 1
            failed_counts["errors"].append(f"{unit_label}: {error}")
            _add_counts(totals, failed_counts)
            event_type = "state_failed" if current_state else "source_failed"
            _create_event(
                db,
                run_id,
                event_type,
                f"Backfill failed for {unit_label}: {error}",
                payload={
                    "state_code": current_state,
                    "error": str(error),
                },
            )
            if not dry_run:
                snapshot_ids.append(
                    _create_coverage_snapshot(
                        db,
                        source=source,
                        state_code=current_state,
                        start_at=start_at,
                        end_at=end_at,
                        filters=unit_filters,
                        counts=failed_counts,
                        status="failed",
                        run_id=run_id,
                    )
                )

    ingestion_run = db.get(IngestionRun, run_id)
    if ingestion_run is None:
        raise RuntimeError(f"Ingestion run {run_id} was not found")

    if dry_run:
        final_status = "dry_run" if successful_units else "failed"
    elif successful_units == len(states):
        final_status = (
            "completed_with_errors"
            if totals["failed_documents"]
            else "completed"
        )
    elif successful_units:
        final_status = "partial"
    else:
        final_status = "failed"

    ingestion_run.run_status = final_status
    ingestion_run.finished_at = datetime.now(timezone.utc)
    ingestion_run.records_found = totals["records_found"]
    ingestion_run.records_saved = totals["new_documents"]
    ingestion_run.new_documents = totals["new_documents"]
    ingestion_run.duplicates_skipped = totals["duplicates_skipped"]
    ingestion_run.failed_documents = totals["failed_documents"]
    ingestion_run.error_message = (
        "; ".join(totals["errors"]) if totals["errors"] else None
    )
    db.commit()
    _create_event(
        db,
        run_id,
        "run_completed" if final_status != "failed" else "run_failed",
        f"Backfill {final_status} for {source}",
        payload={
            "states_attempted": [state for state in states if state],
            "coverage_snapshot_ids": snapshot_ids,
        },
    )
    if not dry_run:
        _update_extraction_status_for_existing(db)

    return {
        "run_id": run_id,
        "status": final_status,
        "source": source,
        "state_code": effective_state,
        "include_all_states": include_all_states,
        "date_range_start": start_date,
        "date_range_end": end_date,
        "records_found": totals["records_found"],
        "new_documents": totals["new_documents"],
        "duplicates_skipped": totals["duplicates_skipped"],
        "failed_documents": totals["failed_documents"],
        "records_preserved": totals["records_preserved"],
        "records_extracted": totals["records_extracted"],
        "coverage_snapshot_id": snapshot_ids[-1] if snapshot_ids else None,
        "coverage_snapshot_ids": snapshot_ids,
        "dry_run": dry_run,
        "filters": filters,
        "errors": totals["errors"],
        "warning": build_backfill_warning(
            source=source,
            state_code=state_code,
            include_all_states=include_all_states,
        ),
        "known_limitations": KNOWN_LIMITATIONS,
    }
