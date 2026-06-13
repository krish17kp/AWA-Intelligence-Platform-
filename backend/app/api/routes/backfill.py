from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.backfill_service import SUPPORTED_SOURCES, run_backfill

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class BackfillPlanRequest(BaseModel):
    source: str = Field(..., description="Data source name")
    start_date: date = Field(..., description="Start date for backfill range")
    end_date: date = Field(..., description="End date for backfill range")
    max_pages: int = Field(default=10, ge=1, description="Maximum pages to fetch")
    dry_run: bool = Field(default=True, description="If true, only return plan without execution")


class BackfillRunRequest(BaseModel):
    source: str = Field(..., description="Data source name")
    start_date: date = Field(default_factory=lambda: date(2026, 1, 1), description="Start date")
    end_date: date = Field(default_factory=lambda: date(2026, 6, 13), description="End date")
    max_pages: int = Field(default=2, ge=1, le=50, description="Maximum pages to fetch")
    page_size: int = Field(default=50, ge=1, le=200, description="Records per page")
    dry_run: bool = Field(default=True, description="If true, plan only, no execution")
    force_refresh: bool = Field(default=False, description="If true, re-download even if duplicate exists")


PLANNED_STAGES = [
    "fetch listing",
    "preserve raw source",
    "compute content hash",
    "dedupe by canonical_key/content_hash",
    "extract text/OCR",
    "store metadata",
    "update coverage",
]


@router.post("/backfill/plan")
def create_backfill_plan(request: BackfillPlanRequest):
    if request.source not in SUPPORTED_SOURCES:
        return {
            "error": True,
            "message": f"Unsupported source '{request.source}'. Supported sources: {', '.join(SUPPORTED_SOURCES)}",
        }

    return {
        "source": request.source,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "max_pages": request.max_pages,
        "dry_run": request.dry_run,
        "planned_stages": PLANNED_STAGES,
        "warning": "This endpoint only creates a plan. Full historical backfill is not complete until run logs and coverage records prove it.",
    }


@router.post("/backfill/run")
def execute_backfill_run(
    request: BackfillRunRequest,
    db: Session = Depends(get_db),
):
    if request.source not in SUPPORTED_SOURCES:
        return {
            "error": True,
            "message": f"Unsupported source '{request.source}'. Supported sources: {', '.join(SUPPORTED_SOURCES)}",
        }

    result = run_backfill(
        db=db,
        source=request.source,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        max_pages=request.max_pages,
        page_size=request.page_size,
        dry_run=request.dry_run,
        force_refresh=request.force_refresh,
    )

    return result