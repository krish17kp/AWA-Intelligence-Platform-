from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.storage_service import _get_storage_mode

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "ok"
    db_error = None
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "error"
        db_error = str(e)

    storage_mode = _get_storage_mode()
    storage_config_ok = all([
        settings.s3_endpoint_url,
        settings.s3_bucket_name,
        settings.aws_access_key_id,
        settings.aws_secret_access_key,
    ]) if storage_mode == "railway_bucket" else True

    storage_status = "ok"
    if storage_mode == "railway_bucket" and not storage_config_ok:
        storage_status = "unknown"
    elif storage_mode == "local":
        storage_status = "ok"

    overall_status = "degraded" if db_status == "error" else "ok"

    return {
        "status": overall_status,
        "service": settings.app_name,
        "version": "0.1.0",
        "database": db_status if db_status == "ok" else db_error,
        "storage": storage_status,
        "storage_mode": storage_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }