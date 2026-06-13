from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class IngestionEvent(Base):
    __tablename__ = "ingestion_events"

    id = Column(Integer, primary_key=True, index=True)

    run_id = Column(
        Integer,
        ForeignKey("ingestion_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_id = Column(
        Integer,
        ForeignKey("source_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    event_type = Column(String(100), nullable=False, index=True)
    message = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)