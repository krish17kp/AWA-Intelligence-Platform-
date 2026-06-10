from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.source_document import SourceDocument

router = APIRouter(prefix="/documents", tags=["documents"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("")
def list_documents(
    source_name: str = None,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    if limit > 100:
        limit = 100

    query = db.query(SourceDocument).order_by(SourceDocument.created_at.desc())

    if source_name:
        query = query.filter(SourceDocument.source_name == source_name)

    documents = query.limit(limit).all()

    return [
        {
            "id": document.id,
            "source_name": document.source_name,
            "source_type": document.source_type,
            "source_url": document.source_url,
            "document_title": document.document_title,
            "document_date": document.document_date,
            "retrieved_at": document.retrieved_at,
            "content_hash": document.content_hash,
            "storage_path": document.storage_path,
        }
        for document in documents
    ]

@router.get("/{document_id}")
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = (
        db.query(SourceDocument)
        .filter(SourceDocument.id == document_id)
        .first()
    )

    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": document.id,
        "source_name": document.source_name,
        "source_type": document.source_type,
        "source_url": document.source_url,
        "document_title": document.document_title,
        "document_date": document.document_date,
        "retrieved_at": document.retrieved_at,
        "content_hash": document.content_hash,
        "storage_path": document.storage_path,
        "mime_type": document.mime_type,
        "file_size_bytes": document.file_size_bytes,
        "raw_metadata_json": document.raw_metadata_json,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }