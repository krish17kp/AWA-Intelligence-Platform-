import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.ingestion_run import IngestionRun
from app.models.source_document import SourceDocument
from app.services.ingestion.aphis_adapter import (
    ingest_enforcement_actions,
    ingest_inspection_reports,
)
from app.services.ingestion.run_service import (
    run_ecfr_ingestion,
    run_federal_register_ingestion,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_ingestion_api_key(
    x_api_key: str | None = Header(default=None, alias="x-api-key"),
) -> None:
    configured_key = settings.ingestion_api_key
    if not configured_key:
        raise HTTPException(
            status_code=503,
            detail="INGESTION_API_KEY is not configured",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, configured_key):
        raise HTTPException(status_code=401, detail="Invalid ingestion API key")


class FederalRegisterRunRequest(BaseModel):
    per_page: int = Field(default=5, ge=1, le=100)


class AphisInspectionRunRequest(BaseModel):
    state_code: str = Field(default="TX", min_length=2, max_length=2)
    license_type: str | None = None
    max_pages: int = Field(default=0, ge=0)
    max_facilities_per_page: int = Field(default=0, ge=0)
    max_documents: int = Field(default=0, ge=0)
    headless: bool = True


class AphisEnforcementRunRequest(BaseModel):
    max_pages: int = Field(default=0, ge=0)
    max_documents: int = Field(default=0, ge=0)
    headless: bool = True


def pending_source_response(
    *,
    source_name: str,
    source_subtype: str,
) -> dict:
    return {
        "source_name": source_name,
        "source_type": source_subtype,
        "source_subtype": source_subtype,
        "status": "source_behavior_pending",
        "records_found": 0,
        "records_saved": 0,
        "duplicates_skipped": 0,
        "changed_records": 0,
        "errors": [],
        "ingestion_run_id": None,
    }


@router.get("/summary")
def ingestion_summary(db: Session = Depends(get_db)):
    documents_by_source = {
        source_name: count
        for source_name, count in (
            db.query(
                SourceDocument.source_name,
                func.count(SourceDocument.id),
            )
            .group_by(SourceDocument.source_name)
            .order_by(SourceDocument.source_name)
            .all()
        )
    }
    latest_runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.created_at.desc())
        .limit(10)
        .all()
    )

    return {
        "total_documents": db.query(SourceDocument).count(),
        "total_ingestion_runs": db.query(IngestionRun).count(),
        "documents_by_source": documents_by_source,
        "latest_ingestion_runs": [
            {
                "id": run.id,
                "source_name": run.source_name,
                "run_status": run.run_status,
                "started_at": run.started_at,
                "finished_at": run.finished_at,
                "records_found": run.records_found,
                "records_saved": run.records_saved,
                "error_message": run.error_message,
            }
            for run in latest_runs
        ],
        "storage_mode": settings.raw_storage_mode,
    }


@router.post("/ecfr/run", dependencies=[Depends(require_ingestion_api_key)])
def run_ecfr(db: Session = Depends(get_db)):
    try:
        return run_ecfr_ingestion(db)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/federal-register/run",
    dependencies=[Depends(require_ingestion_api_key)],
)
def run_federal_register(
    request: FederalRegisterRunRequest | None = None,
    db: Session = Depends(get_db),
):
    request = request or FederalRegisterRunRequest()
    try:
        return run_federal_register_ingestion(db, per_page=request.per_page)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/aphis/inspection-reports/run",
    dependencies=[Depends(require_ingestion_api_key)],
)
def run_aphis_inspection_reports(
    request: AphisInspectionRunRequest | None = None,
    db: Session = Depends(get_db),
):
    request = request or AphisInspectionRunRequest()
    try:
        return ingest_inspection_reports(
            db=db,
            state_code=request.state_code,
            license_type=request.license_type,
            max_pages=request.max_pages,
            max_facilities_per_page=request.max_facilities_per_page,
            max_documents=request.max_documents,
            headless=request.headless,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/aphis/enforcement-actions/run",
    dependencies=[Depends(require_ingestion_api_key)],
)
def run_aphis_enforcement_actions(
    request: AphisEnforcementRunRequest | None = None,
    db: Session = Depends(get_db),
):
    request = request or AphisEnforcementRunRequest()
    try:
        return ingest_enforcement_actions(
            db=db,
            max_pages=request.max_pages,
            max_documents=request.max_documents,
            headless=request.headless,
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/aphis/licensed-registered-persons/run",
    dependencies=[Depends(require_ingestion_api_key)],
)
def run_aphis_licensed_registered_persons(
):
    return pending_source_response(
        source_name="aphis_public_search_tool",
        source_subtype="licensed_registered_persons",
    )


@router.post(
    "/aphis/annual-reports/run",
    dependencies=[Depends(require_ingestion_api_key)],
)
def run_aphis_annual_reports(
):
    return pending_source_response(
        source_name="aphis_public_search_tool",
        source_subtype="annual_reports",
    )


@router.post(
    "/foia/logs/run",
    dependencies=[Depends(require_ingestion_api_key)],
)
def run_foia_logs(
):
    return pending_source_response(
        source_name="foia_returns",
        source_subtype="logs",
    )
