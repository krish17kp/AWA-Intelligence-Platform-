# Required Handoff Report After Implementation

Date: June 10, 2026

## 1. Summary of Work Done

Implemented the missing Railway/n8n ingestion API surface:

- Added public `GET /ingestion/summary`.
- Added authenticated POST routes for eCFR, Federal Register, APHIS inspection reports, APHIS enforcement actions, APHIS licensed/registered-person records, APHIS annual reports, and FOIA logs.
- Added `x-api-key` protection using `INGESTION_API_KEY`.
- Added exact source-document deduplication with text-block reassignment.
- Added shared ingestion-run tracking and source-document persistence for API-triggered ingestion.
- Added n8n-supplied JSON record ingestion for licensed/registered persons, annual reports, and FOIA logs.
- Registered ingestion and maintenance routers in FastAPI.
- Replaced the incorrectly named Railway `Profile` with `Procfile`.
- Configured Railway startup to run `alembic upgrade head` before Uvicorn.
- Added the permanent handoff-report requirement to `command.md`.

## 2. Files Created or Modified

```text
command.md - retained the current task instructions and added the permanent required handoff-report rule
AGENT_HANDOFF.md - updated implementation, verification, command output, and readiness report
backend/Procfile - added Railway migration plus Uvicorn startup command
backend/Profile - removed incorrectly named Railway process file
backend/README.md - documented ingestion API key and new API routes
backend/app/core/config.py - added INGESTION_API_KEY setting
backend/app/main.py - registered ingestion and maintenance routers
backend/app/api/routes/ingestion.py - added summary and all requested ingestion endpoints with API-key protection
backend/app/api/routes/maintenance.py - added exact source-document deduplication endpoint
backend/app/services/ingestion/run_service.py - added shared eCFR, Federal Register, supplied-record persistence, dedupe, and ingestion-run logic
```

## 3. Commands Run

Required commands:

```powershell
cd backend
python scripts\create_local_tables.py
python scripts\show_data_sources.py
python scripts\collect_ecfr_sample.py
python scripts\collect_federal_register_sample.py
python scripts\smoke_test_ingestion.py
```

Additional verification commands:

```powershell
alembic upgrade head
python -m compileall -q app scripts
git diff --check
uvicorn app.main:app --host 127.0.0.1 --port 8011
uvicorn app.main:app --host 127.0.0.1 --port 8012
git switch -c codex/add-ingestion-api-routes
git add AGENT_HANDOFF.md command.md backend/Procfile backend/Profile backend/README.md backend/app/core/config.py backend/app/main.py backend/app/api/routes/ingestion.py backend/app/api/routes/maintenance.py backend/app/services/ingestion/run_service.py
git commit -m "Add authenticated ingestion API routes"
git push -u origin codex/add-ingestion-api-routes
```

API requests were executed with PowerShell `Invoke-WebRequest` and
`Invoke-RestMethod` against ports 8000, 8011, and 8012.

## 4. Command Outputs

### `python scripts\create_local_tables.py`

```text
Database tables registered in SQLAlchemy:
dict_keys(['source_documents', 'ingestion_runs', 'document_text_blocks'])
Local database tables created successfully.
```

### `python scripts\show_data_sources.py`

```text
AWA Intelligence Platform data sources
--------------------------------------
Source: APHIS AWA Public Search Tool
Internal name: aphis_public_search_tool
Type: awa_records
Base URL: https://aphis.my.site.com/PublicSearchTool/s/
Access method: python_adapter_or_manual_browser_discovery
Priority: 1
Record types:
 - inspection_reports
 - enforcement_actions
 - licensed_registered_persons
 - annual_reports
 - teachable_moments
Notes: Main source for AWA inspection reports and enforcement records.
--------------------------------------
Source: Federal Register API
Internal name: federal_register
Type: regulatory_records
Base URL: https://www.federalregister.gov/api/v1/documents.json
Access method: api
Priority: 2
Record types:
 - rules
 - notices
 - proposed_rules
 - public_comments_related_records
Notes: Used for animal welfare regulatory notices and rules. No API key required.
--------------------------------------
Source: eCFR API
Internal name: ecfr
Type: regulatory_citations
Base URL: https://www.ecfr.gov/api/
Access method: api
Priority: 3
Record types:
 - 9_cfr_citations
 - regulatory_text
 - citation_mapping
Notes: Used to map violation citations to official regulatory text.
--------------------------------------
Source: FOIA Returns
Internal name: foia_returns
Type: foia_documents
Base URL: None
Access method: manual_upload_later
Priority: 4
Record types:
 - foia_request
 - foia_response
 - appeal
 - agency_correspondence
Notes: Later phase. Should be designed for, but not implemented today.
--------------------------------------
```

### `python scripts\collect_ecfr_sample.py`

```text
eCFR sample collection completed.
Records saved: 1
Raw file saved at: storage\raw\ecfr\2026-06-10\ecfr_title_9_sample_20260610_110159.xml
```

### `python scripts\collect_federal_register_sample.py`

```text
Federal Register sample collection completed.
Records found: 5
Records saved: 5
Raw file saved at: storage\raw\federal_register\2026-06-10\federal_register_animal_welfare_20260610_110210.json
```

### `python scripts\smoke_test_ingestion.py`

```text
=== AWA Intelligence Platform - Smoke Test ===

Database type: SQLite
Database URL: sqlite:///./local.db

Tables registered in SQLAlchemy metadata:
  - source_documents
  - ingestion_runs
  - document_text_blocks

Tables existing in database:
  - alembic_version
  - document_text_blocks
  - ingestion_runs
  - source_documents

Source documents: 9
Ingestion runs: 17
Document text blocks: 0

Documents by source:
  aphis_public_search_tool: 3
  ecfr: 1
  federal_register: 5

Latest 5 source documents:
  ID: 22 | Source: aphis_public_search_tool | Type: awa_enforcement_action | Title: APHIS enforcement action - Teresa Rauch - Decision and Order...
  ID: 21 | Source: aphis_public_search_tool | Type: awa_inspection_report | Title: APHIS inspection report - Unknown facility (74-B-0410) - 202...
  ID: 13 | Source: aphis_public_search_tool | Type: awa_inspection_report | Title: Manual APHIS Sample - Inspection Report...
  ID: 2 | Source: federal_register | Type: Notice | Title: M15 General Principles for Model-Informed Drug Development; ...
  ID: 3 | Source: federal_register | Type: Notice | Title: M11 Clinical Electronic Structured Harmonised Protocol (CeSH...

Ingestion runs by source:
  aphis_public_search_tool: 8
  ecfr: 4
  federal_register: 4
  foia_returns: 1

Latest 5 ingestion runs:
  ID: 17 | Source: foia_returns | Status: success | Found: 0 | Saved: 0
  ID: 16 | Source: federal_register | Status: success | Found: 5 | Saved: 5
  ID: 15 | Source: ecfr | Status: success | Found: 1 | Saved: 1
  ID: 14 | Source: aphis_public_search_tool | Status: success | Found: 1 | Saved: 0
  ID: 13 | Source: aphis_public_search_tool | Status: success | Found: 1 | Saved: 1

=== Smoke Test Complete ===
```

### `alembic upgrade head`

```text
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
```

## 5. API Verification

All required URLs worked locally:

```text
200 http://127.0.0.1:8000/health
Response: {"status":"ok","service":"awa-intelligence-api"}

200 http://127.0.0.1:8000/documents
Response count: 9

200 http://127.0.0.1:8000/ingestion-runs
Response count: 17

200 http://127.0.0.1:8000/documents/1
Response: eCFR source document ID 1 with full provenance metadata
```

The issue endpoint now works:

```text
200 http://127.0.0.1:8000/ingestion/summary
```

It returned:

```json
{
  "total_documents": 9,
  "total_ingestion_runs": 17,
  "documents_by_source": {
    "aphis_public_search_tool": 3,
    "ecfr": 1,
    "federal_register": 5
  },
  "storage_mode": "local"
}
```

Authentication and maintenance verification:

```text
401 POST /ingestion/foia/logs/run without x-api-key
200 POST /ingestion/foia/logs/run with x-api-key
200 POST /maintenance/dedupe-source-documents with x-api-key
```

The maintenance run found 7 exact duplicate groups and deleted 19 duplicate
rows. Distinct records were retained because the key includes source name,
source type, source URL, and content hash.

## 6. Errors or Failed Items

No required implementation item remains failed.

The first authenticated POST check used an already-running process on port
8000 that had started without `INGESTION_API_KEY`. Its exact response was:

```json
{"detail":"INGESTION_API_KEY is not configured"}
```

This is the intended secure behavior. The check was repeated on isolated port
8012 with `INGESTION_API_KEY` set and returned `200`.

The local database still contains historical ingestion run ID 9 from an
earlier APHIS selector failure:

```text
APHIS State filter was not found
```

That selector was fixed before this implementation and current APHIS runs
succeed.

## 7. Remaining Work

- Set `INGESTION_API_KEY` in Railway and n8n secrets.
- Confirm Railway uses `backend` as its root directory so `backend/Procfile`
  is discovered.
- Licensed/registered-person, annual-report, and FOIA endpoints currently
  preserve records supplied by n8n; autonomous remote collectors for those
  sources remain future work.
- Move raw source storage from the local filesystem to durable object storage.
- OCR, frontend, AI, Neo4j, Dagster, and Celery were intentionally not built.

## 8. Supabase Readiness

The metadata/database layer is ready to switch from SQLite to Supabase
PostgreSQL:

- `DATABASE_URL` supports `postgres://` conversion to `postgresql://`.
- `psycopg2-binary` is installed.
- Alembic migrations are configured and run before Railway startup.
- SQLAlchemy models use PostgreSQL-compatible column types.

Full production readiness still requires:

- Setting the Supabase PostgreSQL `DATABASE_URL`.
- Running `alembic upgrade head` against Supabase.
- Replacing local raw-file storage with Supabase Storage or another durable
  object store. Database metadata is ready; raw storage is not yet durable.
