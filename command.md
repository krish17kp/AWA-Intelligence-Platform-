You are working on the AWA Intelligence Platform.

Current completed state:

- Frontend product skeleton exists.
- Backend visibility endpoints exist.
- Controlled historical backfill system exists.
- `POST /backfill/run` exists.
- `GET /coverage` reads real coverage_snapshots.
- `GET /ingestion/runs/{run_id}/events` exists.
- Coverage page can preview and run controlled backfill.
- Ingestion page can view event timeline.
- Migration `d5e6f7a8b9c0` added ingestion_events, coverage_snapshots, and new tracking columns.
- Commit exists: `b012e4b` — "Add controlled historical backfill execution and coverage tracking".

Critical known limitations to fix:

- APHIS backfill is currently hardcoded to `state_code="TX"`.
- Full historical APHIS coverage is NOT complete.
- `duplicate_of` column exists but is not populated.
- Railway S3 endpoint URL is still unverified.
- Signed URLs are not implemented for `/documents/{id}/raw`.
- eCFR/Federal Register backfill delegates to existing adapters with their own limits.
- Frontend has no authentication; do not solve auth in this task unless required.

Main goal:
Fix controlled backfill so it is not hardcoded to Texas, improve coverage reporting, and add verification safety before moving to OCR/entity extraction.

Do not rebuild the frontend.
Do not rebuild the ingestion pipeline.
Do not implement OCR/entity extraction/facility profiles/AI/case binder in this task.
Do not claim full historical coverage.

TASK 1: Make APHIS backfill configurable

Update backfill request model for `POST /backfill/run` and `POST /backfill/plan`.

Add optional filters:

- state_code: optional string
- license_type: optional string
- facility_name: optional string
- customer_number: optional string if supported by existing adapter
- include_all_states: boolean default false

Rules:

- If `state_code` is provided, use that state.
- If `include_all_states=true`, iterate over a safe list of US state codes.
- If neither `state_code` nor `include_all_states` is provided, default to a safe small state_code like "TX" but return a warning saying default state was used.
- Do not silently hardcode TX without exposing it in request/response.
- Keep max_pages cap enforced.
- Keep dry_run=true as default.
- Never run unlimited all-state backfill accidentally.

TASK 2: Add state coverage tracking

Update `coverage_snapshots` if needed with safe nullable fields:

- state_code nullable string
- filters_json nullable JSON/text

If migration is needed, make it backward compatible.

When a backfill run completes, coverage snapshot should include:

- source
- source_type
- state_code if used
- date range
- filters_json
- records_found
- records_preserved
- records_extracted
- duplicates_skipped
- failed_documents
- status
- notes

TASK 3: Improve `/coverage`

Update `GET /coverage` to return:

- historical_backfill_status
- sources_attempted
- states_attempted
- date_ranges_attempted
- total_records_by_source
- total_records_by_state
- latest_coverage_snapshots
- last_successful_run
- known_limitations
- explicit message: "Full historical APHIS coverage is not complete unless all required source/date/state ranges have completed coverage snapshots."

Status logic:

- not_started: no documents and no snapshots
- partial: any snapshots or documents exist, but no explicit full coverage verification
- complete: do not return complete in this task

TASK 4: Add all-state dry run safety

If include_all_states=true:

- First require dry_run=true unless request also includes `confirm_large_run=true`.
- Add `confirm_large_run` boolean default false.
- If include_all_states=true and dry_run=false and confirm_large_run=false, return 400 with message:
  "All-state real backfill requires confirm_large_run=true."
- Keep max_pages cap.
- Log one ingestion_run per overall backfill or per state. Choose whichever is simpler, but events must clearly show state-level progress.

TASK 5: Populate duplicate_of when possible

Current dedupe uses canonical_key/content_hash but duplicate_of is not populated.

Improve duplicate handling:

- When duplicate found by canonical_key or content_hash, set duplicate_of to existing source_documents.id if creating a duplicate record.
- If skipping duplicates without creating new source_documents row, record existing document id in ingestion_event payload:
  {
  "duplicate_of": existing_id,
  "matched_on": "canonical_key" or "content_hash"
  }
- Do not create duplicate rows unless force_refresh logic requires it.

TASK 6: Improve `/backfill/run` response

Return:

- run_id
- status
- source
- state_code
- include_all_states
- date_range_start
- date_range_end
- records_found
- new_documents
- duplicates_skipped
- failed_documents
- records_preserved
- records_extracted
- coverage_snapshot_id if created
- warning
- known_limitations

If default state was used, warning should say:
"APHIS backfill defaulted to state_code=TX because no state_code or include_all_states option was provided."

TASK 7: Frontend Coverage page update

Do not rebuild the page. Update the existing Coverage page.

In the Run Controlled Backfill form add:

- State Code input/dropdown
- Include All States checkbox
- Confirm Large Run checkbox
- Display current filters in the run result
- Display states_attempted and total_records_by_state in coverage summary

Rules:

- If Include All States is checked and Dry Run is unchecked, show visible warning.
- If Include All States is checked and Confirm Large Run is unchecked, disable real run button or let API return error and display it clearly.
- Keep the existing warning that full historical APHIS coverage is not complete.

TASK 8: Production verification helper

Create a simple backend script:

`backend/scripts/verify_backfill_readiness.py`

It should check:

- database connection
- required tables exist:
  - source_documents
  - ingestion_runs
  - ingestion_events
  - coverage_snapshots
  - document_text_blocks

- required endpoints are registered if easily checkable
- S3/Railway bucket env vars presence
- warn if storage config is missing or unknown
- print clear PASS/WARN/FAIL summary

Do not require this script to contact external APHIS.

TASK 9: Manual test commands in README or docs

Add a short markdown file:

`docs/backfill_testing.md`

Include:

- dry run single state
- real run single state with max_pages=1
- all-state dry run
- all-state real run safety requirement
- checking coverage
- checking ingestion events
- clear note: "Do not claim full historical coverage until coverage snapshots prove all intended source/date/state ranges were completed."

TASK 10: Verification

Run:

- backend compile check
- alembic upgrade head
- frontend TypeScript check
- frontend build

Manual API tests:

1. POST /backfill/plan with state_code=CA
2. POST /backfill/run dry_run=true state_code=CA max_pages=1
3. POST /backfill/run dry_run=true include_all_states=true max_pages=1
4. POST /backfill/run dry_run=false include_all_states=true confirm_large_run=false should return 400
5. GET /coverage should show states_attempted if snapshots exist
6. GET /ingestion/runs/{run_id}/events should show duplicate_of info when duplicates are skipped

Acceptance criteria:

- APHIS backfill no longer silently hardcoded to TX
- User can select state_code from frontend
- User can run all-state dry run safely
- Real all-state run is blocked unless confirmed
- Coverage shows states attempted
- Coverage shows records by state
- Duplicate skip events include existing document id when possible
- Backfill readiness script exists
- Backfill testing documentation exists
- Existing dashboard/documents/ingestion/coverage pages still build
- No historical completion claim is made

Commit message:
"Parameterize APHIS backfill and improve coverage verification"
