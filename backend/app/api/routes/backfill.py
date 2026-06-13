from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class BackfillPlanRequest(BaseModel):
    source: str = Field(..., description="Data source name")
    start_date: date = Field(..., description="Start date for backfill range")
    end_date: date = Field(..., description="End date for backfill range")
    max_pages: int = Field(default=10, ge=1, description="Maximum pages to fetch")
    dry_run: bool = Field(default=True, description="If true, only return plan without execution")


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
    return {
        "source": request.source,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "max_pages": request.max_pages,
        "dry_run": request.dry_run,
        "planned_stages": PLANNED_STAGES,
        "warning": "This endpoint only creates a plan. Full historical backfill is not complete until run logs and coverage records prove it.",
    }