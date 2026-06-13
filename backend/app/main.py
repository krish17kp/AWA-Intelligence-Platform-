from fastapi import FastAPI

from app.api.routes import documents, extraction, health, ingestion, ingestion_runs, maintenance
from app.api.routes import stats, coverage, backfill
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(stats.router)
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(ingestion_runs.router_v1)
app.include_router(ingestion_runs.router_v2)
app.include_router(ingestion.router)
app.include_router(maintenance.router)
app.include_router(coverage.router)
app.include_router(backfill.router)


@app.get("/")
def root():
    return {
        "message": "AWA Intelligence API is running",
    }