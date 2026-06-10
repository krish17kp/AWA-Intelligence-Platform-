from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from datetime import datetime, timezone

from app.core.database import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.ingestion.ecfr_adapter import fetch_ecfr_title_9_sample


def main():
    db = SessionLocal()

    ingestion_run = IngestionRun(
        source_name="ecfr",
        run_status="running",
        started_at=datetime.now(timezone.utc),
        records_found=1,
        records_saved=0,
    )

    db.add(ingestion_run)
    db.commit()
    db.refresh(ingestion_run)

    try:
        result = fetch_ecfr_title_9_sample()

        source_document = SourceDocument(
            source_name="ecfr",
            source_type="regulatory_citation_mapping",
            source_url=result["source_url"],
            document_title="eCFR Title 9 sample regulatory text",
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

        db.add(source_document)

        ingestion_run.run_status = "success"
        ingestion_run.finished_at = datetime.now(timezone.utc)
        ingestion_run.records_saved = 1

        db.commit()

        print("eCFR sample collection completed.")
        print("Records saved:", 1)
        print("Raw file saved at:", result["storage_path"])

    except Exception as error:
        ingestion_run.run_status = "failed"
        ingestion_run.finished_at = datetime.now(timezone.utc)
        ingestion_run.error_message = str(error)
        db.commit()

        print("eCFR sample collection failed.")
        print("Error:", str(error))

    finally:
        db.close()


if __name__ == "__main__":
    main()