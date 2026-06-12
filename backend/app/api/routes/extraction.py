from fastapi import APIRouter, Depends

from app.api.routes.ingestion import get_db, require_ingestion_api_key
from app.services.extraction_service import backfill_text_extraction
from sqlalchemy.orm import Session

router = APIRouter(prefix="/extraction", tags=["extraction"])


@router.post(
    "/backfill/run",
    dependencies=[Depends(require_ingestion_api_key)],
)
def run_backfill(db: Session = Depends(get_db)):
    return backfill_text_extraction(db)
