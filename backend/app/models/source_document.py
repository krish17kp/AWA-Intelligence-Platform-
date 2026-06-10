from sqlalchemy import BigInteger, Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class SourceDocument(Base):
    __tablename__ = "source_documents"

    id = Column(Integer, primary_key=True, index=True)

    source_name = Column(String(100), nullable=False, index=True)
    source_type = Column(String(100), nullable=False, index=True)
    source_url = Column(Text, nullable=False)

    document_title = Column(Text, nullable=True)
    document_date = Column(DateTime(timezone=True), nullable=True)

    retrieved_at = Column(DateTime(timezone=True), nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)

    storage_path = Column(Text, nullable=False)
    mime_type = Column(String(100), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)

    raw_metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)