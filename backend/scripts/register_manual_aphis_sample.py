from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.hashing_service import sha256_bytes
from app.services.storage_service import save_raw_bytes


def main():
    print("=== APHIS Manual Sample Registration ===")
    print()

    sample_file = Path("storage/raw/aphis/APHIS_SAMPLE_LOG.csv")

    if not sample_file.exists():
        print(f"Sample file not found: {sample_file}")
        print("Please place a manually downloaded APHIS file at that location.")
        print("Expected format: CSV or any file from APHIS Public Search Tool")
        return

    print(f"Reading file: {sample_file}")
    content = sample_file.read_bytes()
    content_hash = sha256_bytes(content)
    file_size = len(content)
    mime_type = "text/csv"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"aphis_manual_sample_{timestamp}.csv"

    storage_path = save_raw_bytes(
        source_name="aphis_public_search_tool",
        filename=filename,
        content=content,
    )

    print(f"File saved to: {storage_path}")
    print(f"Content hash: {content_hash}")
    print(f"File size: {file_size} bytes")
    print()

    db = SessionLocal()

    ingestion_run = IngestionRun(
        source_name="aphis_public_search_tool",
        run_status="running",
        started_at=datetime.now(timezone.utc),
        records_found=1,
        records_saved=0,
    )

    db.add(ingestion_run)
    db.commit()
    db.refresh(ingestion_run)

    try:
        source_document = SourceDocument(
            source_name="aphis_public_search_tool",
            source_type="awa_inspection_report",
            source_url="https://aphis.my.site.com/PublicSearchTool/s/",
            document_title="Manual APHIS Sample - Inspection Report",
            document_date=datetime.now(timezone.utc),
            retrieved_at=datetime.now(timezone.utc),
            content_hash=content_hash,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size_bytes=file_size,
            raw_metadata_json={
                "record_type": "inspection_report",
                "facility_name": "Sample Facility",
                "license_number": "LIC-12345",
                "registration_number": "REG-67890",
                "source": "APHIS AWA Public Search Tool",
                "collection_method": "manual_download",
                "notes": "Manually registered sample for schema validation",
            },
        )

        db.add(source_document)

        ingestion_run.run_status = "success"
        ingestion_run.finished_at = datetime.now(timezone.utc)
        ingestion_run.records_saved = 1

        db.commit()

        print("APHIS manual sample registration completed.")
        print("Records saved: 1")
        print(f"Raw file saved at: {storage_path}")
        print(f"Ingestion run ID: {ingestion_run.id}")

    except Exception as error:
        ingestion_run.run_status = "failed"
        ingestion_run.finished_at = datetime.now(timezone.utc)
        ingestion_run.error_message = str(error)
        db.commit()

        print("APHIS manual sample registration failed.")
        print("Error:", str(error))

    finally:
        db.close()


if __name__ == "__main__":
    main()