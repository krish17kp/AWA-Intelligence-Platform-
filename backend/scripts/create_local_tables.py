from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import Base, engine

# Explicit imports are required so SQLAlchemy registers these tables
from app.models.source_document import SourceDocument
from app.models.ingestion_run import IngestionRun
from app.models.document_text_block import DocumentTextBlock


def main():
    print("Database tables registered in SQLAlchemy:")
    print(Base.metadata.tables.keys())

    Base.metadata.create_all(bind=engine)

    print("Local database tables created successfully.")


if __name__ == "__main__":
    main()