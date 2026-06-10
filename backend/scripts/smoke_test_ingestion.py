from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.database import Base, engine
from app.models.source_document import SourceDocument
from app.models.ingestion_run import IngestionRun
from app.models.document_text_block import DocumentTextBlock
from sqlalchemy import func


def main():
    print("=== AWA Intelligence Platform - Smoke Test ===")
    print()

    db_url = settings.database_url
    if db_url.startswith("postgres://"):
        db_type = "PostgreSQL"
    elif db_url.startswith("sqlite"):
        db_type = "SQLite"
    else:
        db_type = "Unknown"

    print(f"Database type: {db_type}")
    print(f"Database URL (masked): {db_url[:20]}..." if len(db_url) > 20 else f"Database URL: {db_url}")
    print()

    print("Tables registered in SQLAlchemy metadata:")
    tables = list(Base.metadata.tables.keys())
    for table in tables:
        print(f"  - {table}")
    print()

    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print("Tables existing in database:")
    for table in existing_tables:
        print(f"  - {table}")
    print()

    from app.core.database import SessionLocal
    db = SessionLocal()

    try:
        doc_count = db.query(SourceDocument).count()
        run_count = db.query(IngestionRun).count()
        block_count = db.query(DocumentTextBlock).count()

        print(f"Source documents: {doc_count}")
        print(f"Ingestion runs: {run_count}")
        print(f"Document text blocks: {block_count}")
        print()

        if doc_count > 0:
            print("Documents by source:")
            source_counts = db.query(
                SourceDocument.source_name,
                func.count(SourceDocument.id)
            ).group_by(SourceDocument.source_name).all()
            for source_name, count in source_counts:
                print(f"  {source_name}: {count}")
            print()

            print("Latest 5 source documents:")
            docs = db.query(SourceDocument).order_by(SourceDocument.created_at.desc()).limit(5).all()
            for doc in docs:
                print(f"  ID: {doc.id} | Source: {doc.source_name} | Type: {doc.source_type} | Title: {doc.document_title[:60] if doc.document_title else 'N/A'}...")
            print()

        if run_count > 0:
            print("Ingestion runs by source:")
            run_counts = db.query(
                IngestionRun.source_name,
                func.count(IngestionRun.id)
            ).group_by(IngestionRun.source_name).all()
            for source_name, count in run_counts:
                print(f"  {source_name}: {count}")
            print()

            print("Latest 5 ingestion runs:")
            runs = db.query(IngestionRun).order_by(IngestionRun.created_at.desc()).limit(5).all()
            for run in runs:
                print(f"  ID: {run.id} | Source: {run.source_name} | Status: {run.run_status} | Found: {run.records_found} | Saved: {run.records_saved}")

    finally:
        db.close()

    print()
    print("=== Smoke Test Complete ===")


if __name__ == "__main__":
    main()