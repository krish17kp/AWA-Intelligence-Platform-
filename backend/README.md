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

### Create Local Database Tables

```powershell
python scripts\create_local_tables.py
```

### Run Database Migrations (Alembic)

```powershell
alembic upgrade head
```

### Show Data Sources

```powershell
python scripts\show_data_sources.py
```

### Run eCFR Sample Ingestion

```powershell
python scripts\collect_ecfr_sample.py
```

Expected output:
```
eCFR sample collection completed.
Records saved: 1
Raw file saved at: storage/raw/ecfr/YYYY-MM-DD/ecfr_title_9_sample_YYYYMMDD_HHMMSS.xml
```

### Run Federal Register Sample Ingestion

```powershell
python scripts\collect_federal_register_sample.py
```

Expected output:
```
Federal Register sample collection completed.
Records found: X
Records saved: X
Raw file saved at: storage/raw/federal_register/YYYY-MM-DD/federal_register_animal_welfare_YYYYMMDD_HHMMSS.json
```

### Run APHIS Inspection Report Ingestion

Install the Playwright browser once:

```powershell
playwright install chromium
```

Collect one page of Texas inspection reports:

```powershell
python scripts\collect_aphis_inspection_reports.py --state TX --max-pages 1
```

Use `--max-pages 0` for all available pages. The command prints JSON so n8n
can execute it and capture the ingestion result. Raw PDFs are validated,
hashed, deduplicated, and saved under:

For controlled test batches, use `--max-facilities-per-page` and
`--max-documents`. A value of `0` means no limit.

```text
storage/raw/aphis_public_search_tool/YYYY-MM-DD/
```

Collect one APHIS enforcement action PDF:

```powershell
python scripts\collect_aphis_enforcement_actions.py --max-pages 1 --max-documents 1
```

### Run Smoke Test

```powershell
python scripts\smoke_test_ingestion.py
```

### Start Backend Server

```powershell
uvicorn app.main:app --reload
```

Server runs at: `http://127.0.0.1:8000`

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/documents` | GET | List documents (supports `source_name` filter, `limit` param) |
| `/documents/{id}` | GET | Get document detail |
| `/ingestion-runs` | GET | List ingestion runs |

Example queries:
```
http://127.0.0.1:8000/health
http://127.0.0.1:8000/documents
http://127.0.0.1:8000/documents?source_name=ecfr&limit=5
http://127.0.0.1:8000/documents/1
http://127.0.0.1:8000/ingestion-runs
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
      ingestion/        # Source adapters
  scripts/              # Runnable scripts
  storage/raw/          # Raw source file storage
  alembic/              # Database migrations
```

## Current Limitations

- SQLite only (PostgreSQL/Supabase planned next)
- No authentication
- APHIS automation currently covers inspection report and enforcement action PDFs
- No OCR or AI features
- No frontend dashboard
- No vector search or graph database

## Next Steps

1. Connect to Supabase PostgreSQL
2. Extend APHIS collection to other record types
3. Add OCR pipeline for PDF processing
4. Build vector search for document retrieval
5. Add authentication and authorization
