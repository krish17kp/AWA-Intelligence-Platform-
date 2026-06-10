from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.routes.ingestion import get_db, require_ingestion_api_key
from app.models.document_text_block import DocumentTextBlock
from app.models.source_document import SourceDocument

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post(
    "/dedupe-source-documents",
    dependencies=[Depends(require_ingestion_api_key)],
)
def dedupe_source_documents(db: Session = Depends(get_db)):
    documents = (
        db.query(SourceDocument)
        .order_by(SourceDocument.id.asc())
        .all()
    )
    keepers: dict[tuple[str, str, str, str], SourceDocument] = {}
    duplicate_groups: set[tuple[str, str, str, str]] = set()
    deleted_ids: list[int] = []

    for document in documents:
        key = (
            document.source_name,
            document.source_type,
            document.source_url,
            document.content_hash,
        )
        keeper = keepers.get(key)
        if keeper is None:
            keepers[key] = document
            continue

        duplicate_groups.add(key)
        (
            db.query(DocumentTextBlock)
            .filter(DocumentTextBlock.source_document_id == document.id)
            .update(
                {DocumentTextBlock.source_document_id: keeper.id},
                synchronize_session=False,
            )
        )
        deleted_ids.append(document.id)
        db.delete(document)

    db.commit()
    return {
        "duplicate_groups_found": len(duplicate_groups),
        "documents_deleted": len(deleted_ids),
        "deleted_document_ids": deleted_ids,
    }
