from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentTextBlock(Base):
    __tablename__ = "document_text_blocks"

    id = Column(Integer, primary_key=True, index=True)

    source_document_id = Column(
        Integer,
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    page_number = Column(Integer, nullable=True)
    block_index = Column(Integer, nullable=True)

    text = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)