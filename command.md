You are working on the AWA Intelligence Platform repository.

Read this carefully before coding.

Current state from the handoff:

- Backend pipeline foundation already works.
- Backend compiles and runs.
- All 4 ingestion adapters work:
  - APHIS inspections
  - APHIS enforcement
  - eCFR
  - Federal Register

- Deduplication via canonical_key works.
- Content hashing works.
- Text extraction works for PDF/XML/JSON.
- 37 documents currently have extracted text.
- Railway Dockerfile deployment works.
- S3-compatible storage with local fallback exists.
- Alembic migration system exists.
- API key auth on ingestion endpoints exists.
- GET /ingestion/summary exists as a basic metrics endpoint.

Critical instruction:
Do NOT rebuild or break the working ingestion pipeline.
Do NOT remove existing routes.
Do NOT rename existing DB columns destructively.
Do NOT introduce fake frontend data.
Do NOT create dummy documents.
Do NOT claim full historical backfill is complete.

Main goal:
The frontend has not been developed at all. Build the frontend product skeleton from zero and add only the minimum backend API contract needed for the frontend to show real data.

Use the Expanded Product Brief direction:

- The product is a defensibility-first evidence and analytics platform.
- Source records must remain preserved.
- Records should show provenance, hash, source URL, extraction status, and review visibility.
- AI is not part of this task today.
- Graph/Neo4j is not part of this task today.
- Dagster is not part of this task today unless existing code already requires it.
- Focus on dashboard, document repository, ingestion visibility, and coverage visibility.

TASK 1: Backend API contract for frontend

A. Enhance GET /health

Current file:
backend/app/api/routes/health.py

Current behavior:
Returns static status only.

Update it to return:

- status: "ok" or "degraded"
- service
- version if available from settings
- database: "ok" or error message
- storage: "ok", "unknown", or error message
- timestamp

Do not make storage check fail the whole endpoint if S3 config is missing. Return "unknown" if not configured.

B. Create GET /stats

Create:
backend/app/api/routes/stats.py

Register it in:
backend/app/main.py

This endpoint must return real DB-derived values only.

Return:

- total_documents
- total_raw_files_preserved
- total_documents_with_text
- total_duplicates_skipped
- total_failed_documents
- total_ingestion_runs
- latest_ingestion_run
- extraction_success_rate
- qa_needed_count

Implementation guidance:

- Use source_documents for total_documents.
- Use source_documents.storage_path not null for total_raw_files_preserved.
- Use document_text_blocks if available for total_documents_with_text.
- If duplicate count is not stored yet, return 0 but add a clear field:
  duplicate_tracking_note: "Duplicate count not fully tracked yet; dedupe currently uses canonical_key/content_hash."
- If failed document count is not available, derive from ingestion_runs if possible, otherwise return 0 with a note.
- qa_needed_count can return 0 until QA queue exists.
- latest_ingestion_run should return latest run from ingestion_runs if available.
- extraction_success_rate = total_documents_with_text / total_documents \* 100, rounded to 2 decimals. If total_documents is 0, return 0.

C. Enhance GET /documents

Current file:
backend/app/api/routes/documents.py

Keep existing behavior but add frontend-friendly parameters:

- page: int default 1
- page_size: int default 25
- q: optional string
- source_type: optional string
- extraction_status: optional string
- date_from: optional date
- date_to: optional date

Return paginated response:
{
"items": [...],
"page": 1,
"page_size": 25,
"total": 37
}

Each item must include:

- id
- title, mapped from document_title
- source_name
- source_type
- source_url
- document_date
- retrieved_at
- content_hash
- canonical_key
- raw_storage_path, mapped from storage_path
- text_extracted boolean
- extraction_status
- duplicate_of if available, else null

Important:
If extraction_status column does not exist yet, do not crash. Compute:

- "extracted" if document has text blocks
- "pending" if no text blocks
  If duplicate_of column does not exist, return null.

D. Keep GET /documents/{id}

Do not break this endpoint.
Make sure the response is frontend-friendly:

- include title alias for document_title
- include raw_storage_path alias for storage_path
- include raw_metadata_json

E. Create GET /documents/{id}/text

Return extracted text from document_text_blocks.

Response:
{
"document_id": "...",
"text_available": true,
"block_count": 3,
"extracted_text": "...",
"extraction_status": "extracted"
}

If no text exists:
{
"document_id": "...",
"text_available": false,
"block_count": 0,
"extracted_text": "",
"extraction_status": "pending"
}

F. Create GET /documents/{id}/raw

Do not overcomplicate signed URLs today.

Return:
{
"document_id": "...",
"storage_available": true/false,
"raw_storage_path": "...",
"source_url": "...",
"download_url": null,
"note": "Signed URL not implemented yet; use source_url or storage path."
}

If storage path exists, storage_available true. If not, false.

G. Add alias GET /ingestion/runs

Current code has /ingestion-runs.
Add /ingestion/runs as an alias without removing /ingestion-runs.

Return frontend-friendly fields:

- run_id
- source
- run_type
- status
- started_at
- completed_at
- records_found
- new_documents
- duplicates_skipped
- failed_documents
- date_range_start
- date_range_end
- error_message

Map existing fields safely:

- source_name -> source
- run_status -> status
- finished_at -> completed_at
- records_saved -> new_documents if new_documents field does not exist
- missing fields should return null or 0, not crash.

H. Create GET /coverage

Create:
backend/app/api/routes/coverage.py

Register it in main.py.

This endpoint should honestly summarize current historical coverage.

Return:
{
"historical_backfill_status": "partial",
"message": "Full historical APHIS coverage is not complete yet. Current data reflects available ingestion runs and stored documents only.",
"total_documents": 37,
"total_documents_with_text": 37,
"sources_attempted": [...],
"date_ranges_attempted": [...],
"total_records_by_source": {...},
"last_successful_run": {...},
"coverage_snapshots": []
}

If coverage_snapshots table does not exist, do not fail. Infer from source_documents and ingestion_runs and return empty coverage_snapshots.

I. Create POST /backfill/plan

Create:
backend/app/api/routes/backfill.py

This endpoint does NOT run scraping.

Input:
{
"source": "aphis_inspections",
"start_date": "2020-01-01",
"end_date": "2026-06-13",
"max_pages": 10,
"dry_run": true
}

Return:
{
"source": "...",
"start_date": "...",
"end_date": "...",
"max_pages": 10,
"dry_run": true,
"planned_stages": [
"fetch listing",
"preserve raw source",
"compute content hash",
"dedupe by canonical_key/content_hash",
"extract text/OCR",
"store metadata",
"update coverage"
],
"warning": "This endpoint only creates a plan. Full historical backfill is not complete until run logs and coverage records prove it."
}

TASK 2: Avoid risky migrations unless necessary

The handoff says new schema columns are missing, but for today the frontend can work without forcing all schema changes.

Do this:

- Prefer API-level computed fields where possible.
- Do not add destructive migrations.
- Only add migrations if they are required for code to run.
- If adding migration, make it backward-compatible and nullable/defaulted.
- Do not rename columns like document_title or source_name.
- Use aliases in API response instead.

Reason:
The priority is frontend product visibility. Schema hardening can continue after the frontend is alive.

TASK 3: Build frontend from zero

The frontend directory currently contains only .gitkeep.

Create React + Vite + TypeScript + Tailwind frontend.

Required files:

- frontend/package.json
- frontend/index.html
- frontend/vite.config.ts
- frontend/tsconfig.json
- frontend/tailwind.config.js
- frontend/postcss.config.js
- frontend/src/main.tsx
- frontend/src/App.tsx
- frontend/src/api/client.ts
- frontend/src/components/Layout.tsx
- frontend/src/components/Card.tsx
- frontend/src/components/DataTable.tsx
- frontend/src/components/StateMessage.tsx
- frontend/src/pages/Dashboard.tsx
- frontend/src/pages/Documents.tsx
- frontend/src/pages/DocumentDetail.tsx
- frontend/src/pages/Ingestion.tsx
- frontend/src/pages/Coverage.tsx
- frontend/src/pages/FutureModules.tsx
- frontend/src/index.css

Use:

- React
- Vite
- TypeScript
- Tailwind CSS
- react-router-dom

TASK 4: Frontend API client

Create frontend/src/api/client.ts

API base URL:

- Use import.meta.env.VITE_API_BASE_URL
- Default fallback: http://localhost:8000

Create functions:

- getHealth()
- getStats()
- getDocuments(params)
- getDocument(id)
- getDocumentText(id)
- getDocumentRaw(id)
- getIngestionRuns()
- getCoverage()
- createBackfillPlan(payload)

Handle errors cleanly.
Do not crash pages if endpoint returns missing fields.

TASK 5: Frontend layout

Create a clean dashboard-style layout:

- Left sidebar
- Top header
- Main content area

Sidebar links:

- Dashboard
- Documents
- Ingestion
- Coverage
- Future Modules

Default route:

- / redirects to /dashboard

Use a simple professional design:

- light background
- cards
- tables
- badges
- readable spacing
- no excessive animations
- no fake charts unless values are real

TASK 6: Dashboard page

Route:
/dashboard

Call:
GET /stats

Show metric cards:

- Total Documents
- Raw Files Preserved
- Documents With Text
- Duplicates Skipped
- Failed Documents
- Ingestion Runs
- Extraction Success Rate
- QA Needed

Also show:

- Latest ingestion run card
- Backend health summary if easy to include

Rules:

- If data is missing, show "Not available yet".
- No hardcoded fake stats.
- If API fails, show error state with retry.

TASK 7: Documents page

Route:
/documents

Call:
GET /documents

Features:

- Search input q
- Source type filter
- Extraction status filter
- Page/page_size support
- Table columns:
  - Title
  - Source Type
  - Source Name
  - Retrieved At
  - Hash short version
  - Extraction Status badge
  - Raw Preserved yes/no
  - View button

Click View goes to:
/documents/:id

If no documents, show empty state:
"No documents available yet. Run ingestion to populate the repository."

TASK 8: Document detail page

Route:
/documents/:id

Call:

- GET /documents/{id}
- GET /documents/{id}/text
- GET /documents/{id}/raw

Show:

- Title
- Source name/type
- Source URL as clickable link
- Document date
- Retrieved timestamp
- Canonical key
- Content hash
- Raw storage path
- Storage availability
- Extracted text preview
- Full extracted text section with scrollable box
- Metadata JSON panel

No AI summary on this page yet.
No fake entity extraction yet.

TASK 9: Ingestion page

Route:
/ingestion

Call:
GET /ingestion/runs

Show table:

- Run ID
- Source
- Run Type
- Status
- Started At
- Completed At
- Records Found
- New Documents
- Duplicates Skipped
- Failed Documents
- Error Message

If /ingestion/runs fails but /ingestion-runs works, the backend alias should fix this. Do not make frontend call old path unless absolutely necessary.

TASK 10: Coverage page

Route:
/coverage

Call:
GET /coverage

Show:

- Historical backfill status
- Big warning box:
  "Full historical APHIS coverage is not complete yet. Current data reflects available ingestion runs and stored documents only."
- Total documents
- Documents with text
- Sources attempted
- Date ranges attempted
- Records by source
- Last successful run
- Coverage snapshots if available

Also add Backfill Plan form:

- source
- start_date
- end_date
- max_pages
- dry_run checkbox
- submit calls POST /backfill/plan
- display planned stages returned by API

Important:
This page must not imply historical data is complete.

TASK 11: Future modules page

Route:
/future-modules

Show disabled cards:

- OCR + QA queue
- Entity extraction
- Facility profiles
- Inspector analytics
- AI research assistant
- Case/evidence binder
- FOIA
- Public portal
- Graph intelligence

Each card should have:

- status: "Planned"
- short reason
- no fake links to unfinished pages

TASK 12: Styling and states

Every page must include:

- loading state
- error state
- empty state
- fallback text for missing fields

Use badges:

- extracted = green
- pending = yellow/gray
- failed = red
- partial = yellow
- complete = green
- not_started = gray

TASK 13: Build/test commands

Add frontend scripts:

- npm run dev
- npm run build
- npm run preview

Backend:

- ensure python compile check passes
- ensure all routers import cleanly

Before finishing, run:

- backend compile check
- frontend npm install
- frontend npm run build

If dependency installation is blocked by environment, still create correct package.json and mention the command needed.

TASK 14: Acceptance criteria

Complete only when:

- frontend directory is no longer empty
- frontend has React/Vite/TypeScript/Tailwind scaffold
- /dashboard exists and calls real /stats
- /documents exists and displays real API documents
- /documents/:id opens detail and text/raw info
- /ingestion exists and displays run history
- /coverage exists and clearly says historical backfill is not complete
- /future-modules exists
- backend has /stats
- backend has /documents/{id}/text
- backend has /documents/{id}/raw
- backend has /coverage
- backend has /backfill/plan
- backend has /ingestion/runs alias
- no fake data
- existing ingestion pipeline is not broken

Commit message:
"Build frontend product skeleton and API visibility endpoints"
