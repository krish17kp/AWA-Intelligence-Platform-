from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.document_text_block import DocumentTextBlock
from app.models.source_document import SourceDocument

router = APIRouter(prefix="/documents", tags=["documents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _has_text_blocks(db: Session, document_id: int) -> bool:
    return (
        db.query(DocumentTextBlock.id)
        .filter(DocumentTextBlock.source_document_id == document_id)
        .first()
        is not None
    )


def _doc_to_response_item(doc: SourceDocument, has_text: bool | None = None) -> dict:
    return {
        "id": doc.id,
        "title": doc.document_title,
        "source_name": doc.source_name,
        "source_type": doc.source_type,
        "source_url": doc.source_url,
        "document_date": doc.document_date.isoformat() if doc.document_date else None,
        "retrieved_at": doc.retrieved_at.isoformat() if doc.retrieved_at else None,
        "content_hash": doc.content_hash,
        "canonical_key": doc.canonical_key,
        "raw_storage_path": doc.storage_path,
        "text_extracted": has_text if has_text is not None else False,
        "extraction_status": "extracted" if has_text else "pending",
        "duplicate_of": None,
    }


@router.get("")
def list_documents(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    extraction_status: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    source_name: str | None = Query(default=None, alias="source_name"),
    limit: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(SourceDocument).order_by(SourceDocument.created_at.desc())

    if source_name:
        query = query.filter(SourceDocument.source_name == source_name)
    if source_type:
        query = query.filter(SourceDocument.source_type == source_type)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            SourceDocument.document_title.ilike(search_term)
            | SourceDocument.source_url.ilike(search_term)
        )
    if date_from:
        query = query.filter(SourceDocument.retrieved_at >= date_from)
    if date_to:
        query = query.filter(SourceDocument.retrieved_at <= date_to)

    total = query.count()

    offset = (page - 1) * page_size
    documents = query.offset(offset).limit(page_size).all()

    doc_ids = [d.id for d in documents]
    doc_ids_with_text = set()
    if doc_ids:
        rows = (
            db.query(DocumentTextBlock.source_document_id)
            .filter(DocumentTextBlock.source_document_id.in_(doc_ids))
            .distinct()
            .all()
        )
        doc_ids_with_text = {row[0] for row in rows}

    items = []
    for doc in documents:
        has_text = doc.id in doc_ids_with_text
        item = _doc_to_response_item(doc, has_text=has_text)
        if extraction_status:
            item_extraction_status = "extracted" if has_text else "pending"
            if item_extraction_status != extraction_status:
                continue
        items.append(item)

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    doc = (
        db.query(SourceDocument)
        .filter(SourceDocument.id == document_id)
        .first()
    )

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    has_text = _has_text_blocks(db, doc.id)

    return {
        "id": doc.id,
        "title": doc.document_title,
        "source_name": doc.source_name,
        "source_type": doc.source_type,
        "source_url": doc.source_url,
        "document_date": doc.document_date.isoformat() if doc.document_date else None,
        "retrieved_at": doc.retrieved_at.isoformat() if doc.retrieved_at else None,
        "content_hash": doc.content_hash,
        "canonical_key": doc.canonical_key,
        "raw_storage_path": doc.storage_path,
        "mime_type": doc.mime_type,
        "file_size_bytes": doc.file_size_bytes,
        "raw_metadata_json": doc.raw_metadata_json,
        "text_extracted": has_text,
        "extraction_status": "extracted" if has_text else "pending",
        "duplicate_of": None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
    }


@router.get("/{document_id}/text")
def get_document_text(document_id: int, db: Session = Depends(get_db)):
    doc = (
        db.query(SourceDocument)
        .filter(SourceDocument.id == document_id)
        .first()
    )

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    blocks = (
        db.query(DocumentTextBlock)
        .filter(DocumentTextBlock.source_document_id == document_id)
        .order_by(DocumentTextBlock.page_number, DocumentTextBlock.block_index)
        .all()
    )

    if not blocks:
        return {
            "document_id": document_id,
            "text_available": False,
            "block_count": 0,
            "extracted_text": "",
            "extraction_status": "pending",
        }

    combined = "\n\n".join(block.text for block in blocks)

    return {
        "document_id": document_id,
        "text_available": True,
        "block_count": len(blocks),
        "extracted_text": combined,
        "extraction_status": "extracted",
    }


@router.get("/{document_id}/raw")
def get_document_raw(document_id: int, db: Session = Depends(get_db)):
    doc = (
        db.query(SourceDocument)
        .filter(SourceDocument.id == document_id)
        .first()
    )

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")

    storage_available = bool(doc.storage_path)

    return {
        "document_id": document_id,
        "storage_available": storage_available,
        "raw_storage_path": doc.storage_path if storage_available else None,
        "source_url": doc.source_url,
        "download_url": None,
        "note": "Signed URL not implemented yet; use source_url or storage path.",
    }