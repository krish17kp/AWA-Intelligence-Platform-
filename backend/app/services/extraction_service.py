import json
import logging
import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Any

from sqlalchemy.orm import Session

from app.models.document_text_block import DocumentTextBlock
from app.models.source_document import SourceDocument
from app.services.storage_service import read_raw_bytes

logger = logging.getLogger(__name__)


def extract_text_blocks(
    db: Session,
    source_document_id: int,
    mime_type: str | None,
    storage_path: str,
    fallback_url: str | None = None,
) -> list[DocumentTextBlock]:
    existing = (
        db.query(DocumentTextBlock.id)
        .filter(DocumentTextBlock.source_document_id == source_document_id)
        .first()
    )
    if existing:
        return []

    raw = read_raw_bytes(storage_path, fallback_url=fallback_url)
    if raw is None:
        logger.warning("Cannot read raw bytes for document %s", source_document_id)
        return []

    blocks: list[DocumentTextBlock] = []
    mime = (mime_type or "").lower()

    try:
        if "pdf" in mime:
            blocks = _extract_pdf(source_document_id, raw)
        elif "xml" in mime:
            blocks = _extract_xml(source_document_id, raw)
        elif "json" in mime:
            blocks = _extract_json(source_document_id, raw)
        else:
            blocks = _extract_text_fallback(source_document_id, raw)
    except Exception as exc:
        logger.warning("Extraction failed for doc %s: %s", source_document_id, exc)
        return []

    for block in blocks:
        db.add(block)
    db.commit()
    return blocks


def _extract_pdf(source_document_id: int, raw: bytes) -> list[DocumentTextBlock]:
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not installed, cannot extract PDF text")
        return []

    try:
        reader = PdfReader(BytesIO(raw))
    except Exception as exc:
        logger.warning("PdfReader failed: %s", exc)
        return []

    blocks: list[DocumentTextBlock] = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        blocks.append(
            DocumentTextBlock(
                source_document_id=source_document_id,
                page_number=page_num,
                block_index=1,
                text=text,
                confidence=1.0,
            )
        )
    return blocks


def _extract_xml(source_document_id: int, raw: bytes) -> list[DocumentTextBlock]:
    try:
        root = ET.fromstring(raw)
        text_parts: list[str] = []
        for elem in root.iter():
            if elem.text and elem.text.strip():
                text_parts.append(elem.text.strip())
        full_text = "\n".join(text_parts)
    except ET.ParseError as exc:
        logger.warning("XML parse failed: %s", exc)
        full_text = raw.decode("utf-8", errors="replace")

    if not full_text.strip():
        return []

    return [
        DocumentTextBlock(
            source_document_id=source_document_id,
            page_number=1,
            block_index=1,
            text=full_text,
            confidence=1.0,
        )
    ]


def _extract_json(source_document_id: int, raw: bytes) -> list[DocumentTextBlock]:
    try:
        parsed = json.loads(raw)
        full_text = json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        full_text = raw.decode("utf-8", errors="replace")

    if not full_text.strip():
        return []

    return [
        DocumentTextBlock(
            source_document_id=source_document_id,
            page_number=1,
            block_index=1,
            text=full_text,
            confidence=1.0,
        )
    ]


def _extract_text_fallback(source_document_id: int, raw: bytes) -> list[DocumentTextBlock]:
    text = raw.decode("utf-8", errors="replace").strip()
    if not text:
        return []
    return [
        DocumentTextBlock(
            source_document_id=source_document_id,
            page_number=1,
            block_index=1,
            text=text,
            confidence=1.0,
        )
    ]


def backfill_text_extraction(db: Session) -> dict[str, Any]:
    docs = db.query(SourceDocument).order_by(SourceDocument.id).all()
    checked = len(docs)
    extracted = 0
    skipped = 0
    text_blocks_created = 0
    errors: list[str] = []

    for doc in docs:
        existing = (
            db.query(DocumentTextBlock.id)
            .filter(DocumentTextBlock.source_document_id == doc.id)
            .first()
        )
        if existing:
            skipped += 1
            continue

        blocks = extract_text_blocks(
            db,
            source_document_id=doc.id,
            mime_type=doc.mime_type,
            storage_path=doc.storage_path,
            fallback_url=doc.source_url,
        )
        if not blocks:
            skipped += 1
            errors.append(f"No text extracted for document {doc.id} ({doc.source_name}/{doc.source_type})")
        else:
            extracted += 1
            text_blocks_created += len(blocks)

    return {
        "status": "success",
        "documents_checked": checked,
        "documents_extracted": extracted,
        "documents_skipped": skipped,
        "text_blocks_created": text_blocks_created,
        "errors": errors,
    }