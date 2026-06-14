from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


class CoverageSnapshot(Base):
    __tablename__ = "coverage_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    source = Column(String(100), nullable=False, index=True)
    source_type = Column(String(100), nullable=True)
    state_code = Column(String(2), nullable=True, index=True)
    filters_json = Column(JSON, nullable=True)
    date_range_start = Column(DateTime(timezone=True), nullable=True)
    date_range_end = Column(DateTime(timezone=True), nullable=True)

    records_found = Column(Integer, nullable=False, default=0)
    records_preserved = Column(Integer, nullable=False, default=0)
    records_extracted = Column(Integer, nullable=False, default=0)
    duplicates_skipped = Column(Integer, nullable=False, default=0)
    failed_documents = Column(Integer, nullable=False, default=0)

    status = Column(String(50), nullable=False, default="partial")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
