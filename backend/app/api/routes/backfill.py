from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.backfill_service import (
    DEFAULT_APHIS_STATE,
    SUPPORTED_SOURCES,
    US_STATE_CODES,
    build_backfill_warning,
    run_backfill,
)

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
    max_pages: int = Field(default=10, ge=1, le=50, description="Maximum pages to fetch")
    dry_run: bool = Field(default=True, description="If true, only return plan without execution")
    state_code: str | None = Field(default=None, min_length=2, max_length=2)
    license_type: str | None = None
    facility_name: str | None = None
    customer_number: str | None = None
    include_all_states: bool = False
    confirm_large_run: bool = False

    @field_validator("state_code")
    @classmethod
    def normalize_state_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class BackfillRunRequest(BaseModel):
    source: str = Field(..., description="Data source name")
    start_date: date = Field(
        default_factory=lambda: date(date.today().year, 1, 1),
        description="Start date",
    )
    end_date: date = Field(default_factory=date.today, description="End date")
    max_pages: int = Field(default=2, ge=1, le=50, description="Maximum pages to fetch")
    page_size: int = Field(default=50, ge=1, le=200, description="Records per page")
    dry_run: bool = Field(default=True, description="If true, plan only, no execution")
    force_refresh: bool = Field(default=False, description="If true, re-download even if duplicate exists")
    state_code: str | None = Field(default=None, min_length=2, max_length=2)
    license_type: str | None = None
    facility_name: str | None = None
    customer_number: str | None = None
    include_all_states: bool = False
    confirm_large_run: bool = False

    @field_validator("state_code")
    @classmethod
    def normalize_state_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


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
    _validate_request(request)

    effective_state = _effective_state(request)
    states = list(US_STATE_CODES) if request.include_all_states else (
        [effective_state] if effective_state else []
    )
    filters = _request_filters(request, effective_state)

    return {
        "source": request.source,
        "start_date": request.start_date.isoformat(),
        "end_date": request.end_date.isoformat(),
        "max_pages": request.max_pages,
        "dry_run": request.dry_run,
        "state_code": effective_state,
        "include_all_states": request.include_all_states,
        "confirm_large_run": request.confirm_large_run,
        "states": states,
        "filters": filters,
        "planned_stages": PLANNED_STAGES,
        "warning": build_backfill_warning(
            source=request.source,
            state_code=request.state_code,
            include_all_states=request.include_all_states,
            plan_only=True,
        ),
    }


@router.post("/backfill/run")
def execute_backfill_run(
    request: BackfillRunRequest,
    db: Session = Depends(get_db),
):
    _validate_request(request)

    result = run_backfill(
        db=db,
        source=request.source,
        start_date=request.start_date.isoformat(),
        end_date=request.end_date.isoformat(),
        max_pages=request.max_pages,
        page_size=request.page_size,
        dry_run=request.dry_run,
        force_refresh=request.force_refresh,
        state_code=request.state_code,
        license_type=request.license_type,
        facility_name=request.facility_name,
        customer_number=request.customer_number,
        include_all_states=request.include_all_states,
    )

    return result


def _validate_request(request: BackfillPlanRequest | BackfillRunRequest) -> None:
    if request.source not in SUPPORTED_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported source '{request.source}'. Supported sources: "
                f"{', '.join(SUPPORTED_SOURCES)}"
            ),
        )
    if request.start_date > request.end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date must be on or before end_date.",
        )
    if request.state_code and request.state_code not in US_STATE_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported state_code '{request.state_code}'.",
        )
    if request.state_code and request.source != "aphis_inspections":
        raise HTTPException(
            status_code=400,
            detail="state_code is only supported for aphis_inspections.",
        )
    if (
        request.source not in ("aphis_inspections", "aphis_enforcement")
        and any(
            (
                request.license_type,
                request.facility_name,
                request.customer_number,
            )
        )
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "license_type, facility_name, and customer_number filters are "
                "only supported for APHIS sources."
            ),
        )
    if request.include_all_states and request.state_code:
        raise HTTPException(
            status_code=400,
            detail="Provide either state_code or include_all_states=true, not both.",
        )
    if request.include_all_states and request.source != "aphis_inspections":
        raise HTTPException(
            status_code=400,
            detail="include_all_states is only supported for aphis_inspections.",
        )
    if (
        request.include_all_states
        and not request.dry_run
        and not request.confirm_large_run
    ):
        raise HTTPException(
            status_code=400,
            detail="All-state real backfill requires confirm_large_run=true.",
        )


def _effective_state(
    request: BackfillPlanRequest | BackfillRunRequest,
) -> str | None:
    if request.source != "aphis_inspections" or request.include_all_states:
        return None
    return request.state_code or DEFAULT_APHIS_STATE


def _request_filters(
    request: BackfillPlanRequest | BackfillRunRequest,
    effective_state: str | None,
) -> dict:
    return {
        "state_code": effective_state,
        "license_type": request.license_type,
        "facility_name": request.facility_name,
        "customer_number": request.customer_number,
        "include_all_states": request.include_all_states,
        "max_pages": request.max_pages,
    }
