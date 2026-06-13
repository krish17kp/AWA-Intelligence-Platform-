You are working on the AWA Intelligence Platform.

Current completed state from the latest handoff:

- Backend product visibility APIs are implemented.
- Frontend React + Vite + TypeScript + Tailwind product skeleton is built.
- Pages implemented:
  - /dashboard
  - /documents
  - /documents/:id
  - /ingestion
  - /coverage
  - /future-modules

- Backend endpoints implemented:
  - GET /health
  - GET /stats
  - GET /documents
  - GET /documents/{id}
  - GET /documents/{id}/text
  - GET /documents/{id}/raw
  - GET /ingestion/runs
  - GET /coverage
  - POST /backfill/plan

- Existing ingestion pipeline must not be broken.
- Existing frontend must not be rebuilt from scratch.
- Full historical APHIS backfill is NOT complete yet.
- /backfill/plan currently only creates a plan and does not run scraping.
- /coverage currently infers status and does not use real coverage_snapshots.
- coverage_snapshots table does not exist yet.
- ingestion_events table does not exist yet.
- /ingestion/runs currently returns run_type/date ranges as null and duplicates/failed counts as 0.
- Existing source_documents may have canonical_key=NULL for older pre-migration records.
- OCR/entity extraction/facility profiles/AI/case binder are not part of this task.

Main goal:
Implement controlled historical backfill execution and real coverage tracking without breaking the existing working pipeline or frontend.

Source of truth:
Use the Expanded Product Brief direction only:

- source preservation before extraction
- provenance and hashes are mandatory
- backfill must be auditable
- do not claim full historical coverage unless run logs and coverage snapshots prove it
- no AI scraping
- no fake statistics
- no dummy data

TASK 1: Add database tables and safe columns

Create an Alembic migration.

A. Create ingestion_events table:

- id
- run_id nullable FK to ingestion_runs.id
- document_id nullable FK to source_documents.id
- event_type string, required
- message text, nullable
- payload json/jsonb nullable
- created_at timestamp default now

Event types should support at least:

- run_started
- listing_fetched
- document_seen
- duplicate_skipped
- raw_preserved
- text_extracted
- document_failed
- run_completed
- run_failed

B. Create coverage_snapshots table:

- id
- source string, required
- source_type string nullable
- date_range_start nullable date/datetime
- date_range_end nullable date/datetime
- records_found integer default 0
- records_preserved integer default 0
- records_extracted integer default 0
- duplicates_skipped integer default 0
- failed_documents integer default 0
- status string default "partial"
- notes text nullable
- created_at timestamp default now

C. Add safe nullable/default columns to ingestion_runs if they do not exist:

- run_type string default "manual"
- date_range_start nullable date/datetime
- date_range_end nullable date/datetime
- new_documents integer default 0
- duplicates_skipped integer default 0
- failed_documents integer default 0

Do not rename existing columns.
Do not remove records_saved/run_status/source_name.
API can map old and new fields.

D. Add safe nullable/default columns to source_documents if they do not exist:

- duplicate_of nullable self-reference if simple to add
- extraction_status string default "pending"
- extraction_method nullable string
- text_storage_path nullable string

Do not break existing records.
For existing records with text blocks, set extraction_status = "extracted" if possible.

TASK 2: Implement real controlled backfill run endpoint

Create or enhance backend route:

POST /backfill/run

This endpoint should execute a controlled backfill run.

Input:
{
"source": "aphis_inspections",
"start_date": "2026-01-01",
"end_date": "2026-06-13",
"max_pages": 2,
"page_size": 50,
"dry_run": false,
"force_refresh": false
}

Required behavior:

- Create an ingestion_runs row at start.
- run_type should be "backfill".
- Save source, date_range_start, date_range_end.
- Create ingestion_events row: run_started.
- Fetch listing using the existing adapter/service for the selected source.
- Do not create a totally separate scraper if working adapters already exist.
- Respect max_pages/page_size.
- For every record found:
  - compute or read canonical_key
  - compute content_hash when raw content is available
  - check duplicate by canonical_key and/or content_hash
  - if duplicate and force_refresh is false:
    - skip it
    - increment duplicates_skipped
    - create ingestion_event duplicate_skipped

  - if new:
    - preserve raw source first
    - store metadata in source_documents
    - extract text using existing text extraction service if available
    - increment new_documents / records_preserved / records_extracted accordingly
    - create ingestion_events for document_seen, raw_preserved, text_extracted

  - if failure:
    - increment failed_documents
    - create ingestion_event document_failed with error payload

- On completion:
  - update ingestion_runs status completed
  - write counts:
    - records_found
    - new_documents
    - duplicates_skipped
    - failed_documents

  - create coverage_snapshots row
  - create ingestion_event run_completed

- On exception:
  - update ingestion_runs status failed
  - write error_message
  - create ingestion_event run_failed
  - return useful error response without hiding the failure.

Important:

- If dry_run = true, do not preserve raw files or insert source_documents.
- In dry_run, still return expected counts if possible and planned actions.
- Do not mark historical_backfill_status complete automatically.
- Mark status partial unless the code has a real source coverage completion check.

TASK 3: Source support

Support these source names if existing adapters allow:

- aphis_inspections
- aphis_enforcement
- federal_register
- ecfr

If a source is unsupported, return 400 with supported source list.

Do not invent successful data for unsupported sources.

TASK 4: Enhance /coverage to use real coverage_snapshots

Update GET /coverage.

It should now:

- read coverage_snapshots if table exists
- include latest snapshots
- include total records by source
- include date ranges attempted
- include last successful backfill run
- include historical_backfill_status

Status logic:

- not_started: no source_documents and no coverage_snapshots
- partial: any documents/snapshots exist but no verified full-source completion
- complete: only if explicit completion flag/check exists later. For now, do not return complete.

Return:
{
"historical_backfill_status": "partial",
"message": "Full historical APHIS coverage is not complete yet. Current data reflects completed backfill runs and coverage snapshots only.",
"sources_attempted": [...],
"date_ranges_attempted": [...],
"total_records_by_source": {...},
"latest_coverage_snapshots": [...],
"last_successful_run": {...},
"known_limitations": [...]
}

TASK 5: Enhance /ingestion/runs

Update /ingestion/runs to return real new fields if migration added them:

- run_type
- date_range_start
- date_range_end
- new_documents
- duplicates_skipped
- failed_documents

Fallback to old fields only if new fields are null.

TASK 6: Add GET /ingestion/runs/{run_id}/events

Create endpoint:
GET /ingestion/runs/{run_id}/events

Return events for a run:

- id
- event_type
- message
- document_id
- payload
- created_at

This will help debugging and demo traceability.

TASK 7: Add frontend support for running controlled backfill

Do not rebuild frontend.

Update existing Coverage page.

Add section:
"Run Controlled Backfill"

Form fields:

- source dropdown:
  - aphis_inspections
  - aphis_enforcement
  - federal_register
  - ecfr

- start_date
- end_date
- max_pages
- page_size
- dry_run checkbox
- force_refresh checkbox

Buttons:

- Preview Plan: calls POST /backfill/plan
- Run Backfill: calls POST /backfill/run

After run:

- show run summary:
  - run_id
  - status
  - records_found
  - new_documents
  - duplicates_skipped
  - failed_documents

- show warning:
  "This does not mean full historical coverage is complete. Coverage is partial until source/date coverage is validated."

Update Ingestion page:

- Add "View Events" action for each run.
- On click, call GET /ingestion/runs/{run_id}/events
- Show event timeline/table:
  - event type
  - message
  - document id
  - timestamp

TASK 8: Add API client functions

Update frontend/src/api/client.ts:

- runBackfill(payload)
- getIngestionRunEvents(runId)

TASK 9: Backfill safety rules

Strictly follow:

- default max_pages should be small, for example 2 or 5
- do not accidentally fetch millions of pages
- no infinite loops
- log failures instead of crashing silently
- do not delete existing documents
- do not overwrite raw preserved source unless force_refresh is true
- do not claim completion
- do not create fake snapshots
- do not create dummy documents

TASK 10: Verification

Run:

- backend compile check
- alembic migration
- frontend TypeScript check
- frontend build

Manual API tests:

- GET /coverage
- POST /backfill/plan
- POST /backfill/run with dry_run=true
- POST /backfill/run with very small real run, max_pages=1
- GET /ingestion/runs
- GET /ingestion/runs/{run_id}/events
- GET /coverage again and confirm snapshot updated

Frontend tests:

- Open /coverage
- Preview plan
- Run dry run
- Run small real backfill
- Confirm run appears in /ingestion
- Confirm events can be viewed
- Confirm /documents count updates only when new documents are actually saved

TASK 11: Acceptance criteria

Complete only when:

- ingestion_events table exists
- coverage_snapshots table exists
- /backfill/run exists
- /backfill/run supports dry_run and real controlled run
- /backfill/run creates ingestion run records
- /backfill/run creates ingestion events
- /backfill/run creates coverage snapshot on completion
- /coverage reads real coverage snapshots
- /ingestion/runs shows real backfill counts
- /ingestion/runs/{run_id}/events works
- Coverage frontend can preview and run controlled backfill
- Ingestion frontend can show run events
- No existing frontend pages are broken
- No existing ingestion adapters are broken
- No fake historical completion claim is made

Commit message:
"Add controlled historical backfill execution and coverage tracking"
