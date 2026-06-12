# AWA Intelligence Platform - Backend

Backend API for the AWA Intelligence Platform built on USDA Animal Welfare Act records.

## Quick Start

### Activate Virtual Environment

```powershell
cd backend
.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Get-Location).Path
```

### Install Dependencies

```powershell
pip install -r requirements.txt
```

### Playwright (for APHIS browser automation)

```powershell
playwright install chromium
```

### Run Database Migrations

```powershell
alembic upgrade head
```

### Show Data Sources

```powershell
python scripts\show_data_sources.py
```

### Start Backend Server

```powershell
uvicorn app.main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

Set an ingestion API key before calling POST ingestion or maintenance routes:

```powershell
$env:INGESTION_API_KEY = "replace-with-a-secret"
```

## Railway Production

**Production URL:** `https://awa-intelligence-platform-production.up.railway.app`

## Railway Docker Deployment

Railway uses `backend/Dockerfile` because the service Root Directory is `backend`.

The Dockerfile uses the official Playwright Python image:

`mcr.microsoft.com/playwright/python:v1.60.0-noble`

This is required because APHIS scraping uses Playwright/Chromium. A normal Python/Railpack build installs the Playwright Python package but does not install Chromium browser binaries, causing APHIS ingestion to fail.

### Railway Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Railway PostgreSQL connection string |
| `INGESTION_API_KEY` | API key for POST ingestion endpoints |
| `RAW_STORAGE_MODE` | Set to `railway_bucket` for S3 bucket storage |
| `S3_ENDPOINT_URL` | Railway Bucket S3-compatible endpoint |
| `S3_BUCKET_NAME` | Railway Bucket name |
| `AWS_ACCESS_KEY_ID` | Railway Bucket access key |
| `AWS_SECRET_ACCESS_KEY` | Railway Bucket secret key |
| `AWS_DEFAULT_REGION` | S3 region (default `us-east-1`)

## API Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root health check |
| `/health` | GET | Health check |
| `/documents` | GET | List documents (supports `source_name`, `limit`) |
| `/documents/{id}` | GET | Get document detail |
| `/ingestion-runs` | GET | List ingestion runs |
| `/ingestion/summary` | GET | Ingestion totals, source counts, latest runs |

### Authenticated Endpoints (require `x-api-key` header)

All POST ingestion endpoints require the `INGESTION_API_KEY` in the `x-api-key` header.

| Endpoint | Method | Source | Description |
|----------|--------|--------|-------------|
| `/ingestion/aphis/inspection-reports/run` | POST | APHIS Public Search Tool | Scrapes APHIS inspection reports via Playwright, downloads PDFs |
| `/ingestion/aphis/enforcement-actions/run` | POST | APHIS Enforcement pages | Scrapes APHIS enforcement actions table, downloads PDFs |
| `/ingestion/aphis/licensed-registered-persons/run` | POST | APHIS Public Search Tool | Not yet implemented — returns `source_behavior_pending` |
| `/ingestion/aphis/annual-reports/run` | POST | APHIS Public Search Tool | Not yet implemented — returns `source_behavior_pending` |
| `/ingestion/ecfr/run` | POST | eCFR API | Fetches Title 9 XML from eCFR versioner API |
| `/ingestion/federal-register/run` | POST | Federal Register API | Fetches AWA/APHIS-related Federal Register documents |
| `/ingestion/foia/logs/run` | POST | FOIA | Not yet implemented — returns `source_behavior_pending` |
| `/maintenance/dedupe-source-documents` | POST | — | Removes exact duplicate source document rows |

### Response Contract (POST ingestion endpoints)

```json
{
  "source_name": "string",
  "source_subtype": "string",
  "status": "success | partial_success | source_behavior_pending | failed",
  "records_found": 0,
  "records_saved": 0,
  "duplicates_skipped": 0,
  "changed_records": 0,
  "errors": [],
  "ingestion_run_id": 0
}
```

## Storage Behavior

### Local Mode (`RAW_STORAGE_MODE=local`)

Raw files are written to `backend/storage/raw/{source_name}/{YYYY-MM-DD}/{filename}`.

### Railway Bucket Mode (`RAW_STORAGE_MODE=railway_bucket`)

Raw files are stored in Railway Bucket with key format:
`sources/{source_name}/{YYYY-MM-DD}/{filename}`

- **No raw files are written to local filesystem** in production mode.
- If Railway Bucket is unreachable, falls back to local storage.
- Storage path is stored in PostgreSQL as `storage_path`.

## Deduplication

Each source document is tagged with a `canonical_key`:
- `aphis:inspection_report:{source_url_or_pdf_url_hash}`
- `aphis:enforcement_action:{source_url_or_pdf_url_hash}`
- `ecfr:title-9:2024-01-01`
- `federal_register:{document_number_or_source_url}`
- `foia:{request_id_or_content_hash}`

Rules:
- Same canonical_key + same hash = skip duplicate.
- Same canonical_key + different hash = preserve as changed version.
- Raw evidence is never overwritten.

## Verifying Production

### Quick Verification Script

```powershell
python scripts\verify_production_ingestion.py --base-url https://awa-intelligence-platform-production.up.railway.app --api-key YOUR_KEY
```

### Storage Backend Test

```powershell
python scripts\test_storage_backend.py
```

### Smoke Test (local)

```powershell
python scripts\smoke_test_ingestion.py
```

## Project Structure

```
backend/
  app/
    api/routes/         # FastAPI route handlers
    core/               # Config, database
    models/             # SQLAlchemy models
    schemas/            # Pydantic schemas
    services/           # Business logic
      ingestion/        # Source adapters (APHIS, eCFR, Federal Register)
  scripts/              # Runnable scripts
  storage/raw/          # Raw source file storage (local mode only)
  alembic/              # Database migrations
```

## Current Limitations

- APHIS licensed/registered persons, annual reports, and FOIA logs are not yet implemented (return `source_behavior_pending`).
- Railway Bucket S3 endpoint must be verified against actual Railway-provided values.
- Federal Register filtering may still capture some non-APHIS records.
- No OCR or AI features.
- No frontend dashboard.
