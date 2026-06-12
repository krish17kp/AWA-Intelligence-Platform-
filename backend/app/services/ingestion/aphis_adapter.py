import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.hashing_service import sha256_bytes
from app.services.pdf_download_service import download_pdf_bytes
from app.services.storage_service import save_raw_bytes

logger = logging.getLogger(__name__)

SOURCE_NAME = "aphis_public_search_tool"
SOURCE_TYPE = "awa_inspection_report"
INSPECTION_REPORTS_URL = (
    "https://aphis.my.site.com/PublicSearchTool/s/inspection-reports"
)
ENFORCEMENT_ACTIONS_URL = (
    "https://www.aphis.usda.gov/animal-care/awa-services/"
    "animal-welfare-horse-protection-actions"
)
PDF_BASE_URL = "https://aphis.file.force.com"
HASH_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def generate_hash_id(url: str) -> str:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if query.get("ids"):
        return query["ids"][0]
    if query.get("oid") and query.get("d"):
        value = query["oid"][0] + query["d"][0]
        return hashlib.md5(value.encode(), usedforsecurity=False).hexdigest()

    return hashlib.md5(url.encode(), usedforsecurity=False).hexdigest()


def normalize_pdf_url(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return urljoin(PDF_BASE_URL, url)


def parse_aphis_date(value: Any) -> datetime | None:
    if not value:
        return None

    text = str(value).strip()
    for date_format in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%m/%d/%Y",
    ):
        try:
            parsed = datetime.strptime(text, date_format)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _record_title(record: dict[str, Any], document_date: datetime | None) -> str:
    facility_name = (
        str(
            record.get("siteName")
            or record.get("legalName")
            or record.get("customerName")
            or record.get("accountName")
            or ""
        ).strip()
        or "Unknown facility"
    )
    certificate = str(record.get("certNumber") or "").strip()
    date_text = document_date.date().isoformat() if document_date else "unknown date"
    suffix = f" ({certificate})" if certificate else ""
    return f"APHIS inspection report - {facility_name}{suffix} - {date_text}"


def _extract_records_from_aura_payload(body: str) -> list[dict[str, Any]]:
    if not body.lstrip().startswith("{"):
        return []

    payload = json.loads(body)
    records: list[dict[str, Any]] = []
    for action in payload.get("actions", []):
        if action.get("state") != "SUCCESS":
            continue
        return_value = action.get("returnValue") or {}
        if not isinstance(return_value, dict):
            continue
        results = return_value.get("results")
        if not isinstance(results, list):
            continue
        records.extend(
            record
            for record in results
            if isinstance(record, dict) and record.get("reportLink")
        )
    return records


def discover_inspection_reports(
    state_code: str = "TX",
    license_type: str | None = None,
    max_pages: int = 1,
    max_facilities_per_page: int = 0,
    max_documents: int = 0,
    headless: bool = True,
) -> list[dict[str, Any]]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Playwright is required. Install requirements and run "
            "'playwright install chromium'."
        ) from error

    state_code = state_code.strip().upper()
    captured_records: list[dict[str, Any]] = []

    def handle_response(response) -> None:
        if "aura" not in response.url or response.status != 200:
            return
        try:
            captured_records.extend(_extract_records_from_aura_payload(response.text()))
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            logger.debug("Could not parse APHIS Aura response: %s", error)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, args=["--no-sandbox"])
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.on("response", handle_response)

        try:
            page.goto(INSPECTION_REPORTS_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            state_select = page.get_by_label("State", exact=True)
            if state_select.count() == 0:
                raise RuntimeError("APHIS State filter was not found")
            state_option = state_select.locator(
                f'option:text-matches("\\\\({state_code}\\\\)$", "i")'
            )
            if state_option.count() == 0:
                raise ValueError(f"APHIS does not list state code {state_code}")
            state_select.select_option(value=state_option.first.get_attribute("value"))

            if license_type:
                type_select = page.get_by_label(
                    "License/Registration Type", exact=True
                )
                if type_select.count() == 0:
                    raise RuntimeError("APHIS Certificate Type filter was not found")
                option_values = type_select.locator("option").evaluate_all(
                    """(options) => options.map((option) => ({
                      value: option.value,
                      label: option.textContent.trim()
                    }))"""
                )
                requested = license_type.strip().casefold()
                selected = next(
                    (
                        option["value"]
                        for option in option_values
                        if option["value"].casefold() == requested
                        or option["label"].casefold() == requested
                    ),
                    None,
                )
                if not selected:
                    raise ValueError(
                        f"APHIS does not list license/registration type {license_type}"
                    )
                type_select.select_option(value=selected)

            search_button = page.locator('button:has-text("Search")')
            if search_button.count() == 0:
                raise RuntimeError("APHIS Search button was not found")
            search_button.first.click()
            page.wait_for_timeout(8000)

            current_page = 1
            while True:
                query_button_count = page.locator(
                    'button[title="Query Inspection Reports"]'
                ).count()
                if max_facilities_per_page > 0:
                    query_button_count = min(
                        query_button_count, max_facilities_per_page
                    )

                page.evaluate(
                    """
                    ({limit}) => {
                      const buttons = Array.from(
                      document.querySelectorAll(
                        'button[title="Query Inspection Reports"]'
                      )
                      ).slice(0, limit);
                      buttons.forEach((button, index) => {
                        setTimeout(() => button.click(), index * 500);
                      });
                    }
                    """
                    ,
                    {"limit": query_button_count},
                )
                page.wait_for_timeout(max(10000, query_button_count * 500 + 5000))

                if max_pages > 0 and current_page >= max_pages:
                    break

                next_button = page.get_by_role("button", name=">", exact=True)
                if next_button.count() == 0 or next_button.first.is_disabled():
                    break
                next_button.first.click()
                page.wait_for_timeout(5000)
                current_page += 1
        except PlaywrightTimeoutError as error:
            raise RuntimeError("APHIS Public Search Tool timed out") from error
        finally:
            browser.close()

    unique_records: dict[str, dict[str, Any]] = {}
    for record in captured_records:
        source_url = normalize_pdf_url(str(record.get("reportLink") or ""))
        source_id = generate_hash_id(source_url)
        if HASH_RE.fullmatch(source_id):
            unique_records[source_id] = record

    records = list(unique_records.values())
    if max_documents > 0:
        return records[:max_documents]
    return records


def discover_enforcement_actions(
    max_pages: int = 1,
    headless: bool = True,
) -> list[dict[str, Any]]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Playwright is required. Install requirements and run "
            "'playwright install chromium'."
        ) from error

    records: list[dict[str, Any]] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            page.goto(
                ENFORCEMENT_ACTIONS_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            page.wait_for_timeout(10000)

            current_page = 1
            while True:
                for row in page.locator("table tbody tr").all():
                    cells = row.locator("td")
                    if cells.count() < 7:
                        continue
                    link = cells.nth(0).locator("a")
                    href = link.get_attribute("href") if link.count() else None
                    if not href:
                        continue

                    records.append(
                        {
                            "dba": cells.nth(0).inner_text().strip(),
                            "certificate_number": cells.nth(2).inner_text().strip(),
                            "customer_number": cells.nth(3).inner_text().strip(),
                            "license_category": cells.nth(4).inner_text().strip(),
                            "action_date": cells.nth(5).inner_text().strip(),
                            "action_type": cells.nth(6).inner_text().strip(),
                            "reportLink": urljoin(ENFORCEMENT_ACTIONS_URL, href),
                        }
                    )

                if max_pages > 0 and current_page >= max_pages:
                    break

                next_button = page.locator("button.dt-paging-button.next")
                classes = (
                    next_button.first.get_attribute("class")
                    if next_button.count()
                    else ""
                )
                if next_button.count() == 0 or "disabled" in (classes or ""):
                    break
                next_button.first.click()
                page.wait_for_timeout(3000)
                current_page += 1
        except PlaywrightTimeoutError as error:
            raise RuntimeError("APHIS enforcement actions page timed out") from error
        finally:
            browser.close()

    unique_records: dict[str, dict[str, Any]] = {}
    for record in records:
        unique_records[record["reportLink"]] = record
    return list(unique_records.values())


def ingest_enforcement_actions(
    db: Session,
    max_pages: int = 1,
    max_documents: int = 0,
    headless: bool = True,
) -> dict[str, Any]:
    ingestion_run = IngestionRun(
        source_name=SOURCE_NAME,
        run_status="running",
        started_at=datetime.now(timezone.utc),
        records_found=0,
        records_saved=0,
    )
    db.add(ingestion_run)
    db.commit()
    db.refresh(ingestion_run)
    ingestion_run_id = ingestion_run.id

    duplicates_skipped = 0
    download_failures = 0
    changed_records = 0
    errors: list[str] = []

    try:
        records = discover_enforcement_actions(
            max_pages=max_pages,
            headless=headless,
        )
        if max_documents > 0:
            records = records[:max_documents]
        ingestion_run.records_found = len(records)

        for record in records:
            source_url = record["reportLink"]
            source_id = generate_hash_id(source_url)
            canonical_key = f"aphis:enforcement_action:{source_id}"

            existing = (
                db.query(SourceDocument)
                .filter(SourceDocument.canonical_key == canonical_key)
                .first()
            )

            if existing:
                duplicates_skipped += 1
                continue

            try:
                content = download_pdf_bytes(source_url)
            except RuntimeError as error:
                download_failures += 1
                errors.append(f"PDF download failed for {source_url}: {error}")
                logger.error("Skipping APHIS enforcement PDF: %s", error)
                continue

            content_hash = sha256_bytes(content)

            document_date = parse_aphis_date(record.get("action_date"))
            title = "APHIS enforcement action"
            if record.get("dba"):
                title += f" - {record['dba']}"
            if record.get("action_type"):
                title += f" - {record['action_type']}"

            storage_path = save_raw_bytes(
                source_name=SOURCE_NAME,
                filename=f"enforcement_{source_id}_{content_hash[:12]}.pdf",
                content=content,
            )

            db.add(
                SourceDocument(
                    source_name=SOURCE_NAME,
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
                    raw_metadata_json={
                        **record,
                        "record_type": "enforcement_action",
                        "collection_method": "playwright_html_table",
                        "source_record_id": source_id,
                    },
                )
            )
            db.commit()
            ingestion_run.records_saved += 1

        ingestion_run.run_status = (
            "partial_success" if download_failures else "success"
        )
        ingestion_run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "source_name": SOURCE_NAME,
            "source_subtype": "enforcement_actions",
            "status": ingestion_run.run_status,
            "records_found": ingestion_run.records_found,
            "records_saved": ingestion_run.records_saved,
            "duplicates_skipped": duplicates_skipped,
            "changed_records": changed_records,
            "errors": errors,
            "ingestion_run_id": ingestion_run_id,
        }
    except Exception as error:
        db.rollback()
        ingestion_run = db.get(IngestionRun, ingestion_run_id)
        if ingestion_run is not None:
            ingestion_run.run_status = "failed"
            ingestion_run.finished_at = datetime.now(timezone.utc)
            ingestion_run.error_message = str(error)
            db.commit()
        raise


def ingest_inspection_reports(
    db: Session,
    state_code: str = "TX",
    license_type: str | None = None,
    max_pages: int = 1,
    max_facilities_per_page: int = 0,
    max_documents: int = 0,
    headless: bool = True,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    ingestion_run = IngestionRun(
        source_name=SOURCE_NAME,
        run_status="running",
        started_at=started_at,
        records_found=0,
        records_saved=0,
    )
    db.add(ingestion_run)
    db.commit()
    db.refresh(ingestion_run)
    ingestion_run_id = ingestion_run.id

    duplicates_skipped = 0
    download_failures = 0
    changed_records = 0
    errors: list[str] = []

    try:
        records = discover_inspection_reports(
            state_code=state_code,
            license_type=license_type,
            max_pages=max_pages,
            max_facilities_per_page=max_facilities_per_page,
            max_documents=max_documents,
            headless=headless,
        )
        ingestion_run.records_found = len(records)

        for record in records:
            raw_link = str(record.get("reportLink") or "").strip()
            source_url = normalize_pdf_url(raw_link)
            source_id = generate_hash_id(source_url)
            canonical_key = f"aphis:inspection_report:{source_id}"

            existing = (
                db.query(SourceDocument)
                .filter(SourceDocument.canonical_key == canonical_key)
                .first()
            )
            if existing:
                duplicates_skipped += 1
                continue

            try:
                content = download_pdf_bytes(source_url)
            except RuntimeError as error:
                download_failures += 1
                errors.append(f"PDF download failed for {source_url}: {error}")
                logger.error("Skipping APHIS PDF after download failure: %s", error)
                continue

            content_hash = sha256_bytes(content)

            storage_path = save_raw_bytes(
                source_name=SOURCE_NAME,
                filename=f"{source_id}_{content_hash[:12]}.pdf",
                content=content,
            )
            retrieved_at = datetime.now(timezone.utc)
            document_date = parse_aphis_date(record.get("inspectionDate"))

            db.add(
                SourceDocument(
                    source_name=SOURCE_NAME,
                    source_type=SOURCE_TYPE,
                    source_url=source_url,
                    document_title=_record_title(record, document_date),
                    document_date=document_date,
                    retrieved_at=retrieved_at,
                    content_hash=content_hash,
                    storage_path=storage_path,
                    mime_type="application/pdf",
                    file_size_bytes=len(content),
                    canonical_key=canonical_key,
                    raw_metadata_json={
                        **record,
                        "record_type": "inspection_report",
                        "collection_method": "playwright_aura_interception",
                        "state_filter": state_code.upper(),
                        "license_type_filter": license_type,
                        "source_record_id": source_id,
                        "raw_report_link": raw_link,
                    },
                )
            )
            db.commit()
            ingestion_run.records_saved += 1

        ingestion_run.run_status = (
            "partial_success" if download_failures else "success"
        )
        ingestion_run.finished_at = datetime.now(timezone.utc)
        db.commit()

        return {
            "source_name": SOURCE_NAME,
            "source_subtype": "inspection_reports",
            "status": ingestion_run.run_status,
            "records_found": ingestion_run.records_found,
            "records_saved": ingestion_run.records_saved,
            "duplicates_skipped": duplicates_skipped,
            "changed_records": changed_records,
            "errors": errors,
            "ingestion_run_id": ingestion_run_id,
        }
    except Exception as error:
        db.rollback()
        ingestion_run = db.get(IngestionRun, ingestion_run_id)
        if ingestion_run is not None:
            ingestion_run.run_status = "failed"
            ingestion_run.finished_at = datetime.now(timezone.utc)
            ingestion_run.error_message = str(error)
            db.commit()
        raise
