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
from sqlalchemy import func, inspect


def main():
    print("=== AWA Intelligence Platform - Smoke Test ===")
    print()

    db_url = settings.database_url
    if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
        db_type = "PostgreSQL"
    elif db_url.startswith("sqlite"):
        db_type = "SQLite"
    else:
        db_type = "Unknown"

    print(f"Database type: {db_type}")
    print(f"Storage mode: {settings.raw_storage_mode}")
    masked = db_url[:30] + "..." if len(db_url) > 30 else db_url
    print(f"Database URL (masked): {masked}")
    print()

    print("Tables registered in SQLAlchemy metadata:")
    for table in sorted(Base.metadata.tables.keys()):
        print(f"  - {table}")
    print()

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print("Tables existing in database:")
    for table in sorted(existing_tables):
        print(f"  - {table}")
    print()

    from app.core.database import SessionLocal
    db = SessionLocal()

    try:
        doc_count = db.query(SourceDocument).count()
        run_count = db.query(IngestionRun).count()
        block_count = db.query(DocumentTextBlock).count()

        print(f"Total source documents: {doc_count}")
        print(f"Total ingestion runs: {run_count}")
        print(f"Document text blocks: {block_count}")
        print()

        if doc_count > 0:
            print("Documents by source:")
            for source_name, count in db.query(
                SourceDocument.source_name, func.count(SourceDocument.id)
            ).group_by(SourceDocument.source_name).order_by(SourceDocument.source_name).all():
                print(f"  {source_name}: {count}")

            print("\nDocuments by subtype:")
            for source_type, count in db.query(
                SourceDocument.source_type, func.count(SourceDocument.id)
            ).group_by(SourceDocument.source_type).order_by(SourceDocument.source_type).all():
                print(f"  {source_type}: {count}")

            dup_count = (
                db.query(SourceDocument.canonical_key, func.count(SourceDocument.id))
                .filter(SourceDocument.canonical_key.isnot(None))
                .group_by(SourceDocument.canonical_key)
                .having(func.count(SourceDocument.id) > 1)
                .count()
            )
            print(f"\nDuplicate canonical keys (potential duplicates): {dup_count}")

            print("\nLatest 5 source documents:")
            for doc in db.query(SourceDocument).order_by(SourceDocument.created_at.desc()).limit(5).all():
                title = (doc.document_title or "")[:60]
                print(f"  ID:{doc.id} | {doc.source_name}/{doc.source_type} | {title}")

        if run_count > 0:
            print("\nIngestion runs by source:")
            for source_name, count in db.query(
                IngestionRun.source_name, func.count(IngestionRun.id)
            ).group_by(IngestionRun.source_name).order_by(IngestionRun.source_name).all():
                print(f"  {source_name}: {count}")

            print("\nLatest 5 ingestion runs:")
            for run in db.query(IngestionRun).order_by(IngestionRun.created_at.desc()).limit(5).all():
                print(f"  ID:{run.id} | {run.source_name} | {run.run_status} | found:{run.records_found} saved:{run.records_saved}")

    finally:
        db.close()

    print()
    print("=== Smoke Test Complete ===")


if __name__ == "__main__":
    main()
