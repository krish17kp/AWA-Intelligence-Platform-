from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.ingestion.federal_register_adapter import (
    fetch_federal_register_animal_welfare_records,
)


def parse_document_date(date_text):
    if not date_text:
        return None

    try:
        return datetime.fromisoformat(date_text).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def main():
    db = SessionLocal()

    ingestion_run = IngestionRun(
        source_name="federal_register",
        run_status="running",
        started_at=datetime.now(timezone.utc),
        records_found=0,
        records_saved=0,
    )

    db.add(ingestion_run)
    db.commit()
    db.refresh(ingestion_run)

    try:
        result = fetch_federal_register_animal_welfare_records(per_page=5)
        raw_json = result["raw_json"]

        records = raw_json.get("results", [])

        saved_count = 0

        for record in records:
            source_url = record.get("html_url") or record.get("pdf_url")

            if not source_url:
                continue

            source_document = SourceDocument(
                source_name="federal_register",
                source_type=record.get("type") or "federal_register_document",
                source_url=source_url,
                document_title=record.get("title"),
                document_date=parse_document_date(record.get("publication_date")),
                retrieved_at=result["retrieved_at"],
                content_hash=result["content_hash"],
                storage_path=result["storage_path"],
                mime_type="application/json",
                file_size_bytes=result["file_size_bytes"],
                raw_metadata_json=record,
            )

            db.add(source_document)
            saved_count = saved_count + 1

        ingestion_run.run_status = "success"
        ingestion_run.finished_at = datetime.now(timezone.utc)
        ingestion_run.records_found = len(records)
        ingestion_run.records_saved = saved_count

        db.commit()

        print("Federal Register sample collection completed.")
        print("Records found:", len(records))
        print("Records saved:", saved_count)
        print("Raw file saved at:", result["storage_path"])

    except Exception as error:
        ingestion_run.run_status = "failed"
        ingestion_run.finished_at = datetime.now(timezone.utc)
        ingestion_run.error_message = str(error)
        db.commit()

        print("Federal Register sample collection failed.")
        print("Error:", str(error))

    finally:
        db.close()


if __name__ == "__main__":
    main()