Before making any changes, read `command.md` fully.

We have completed Railway + n8n production ingestion verification. Now fix the remaining production data-quality issues.

Current verified production state:

- `source_documents` has 37 records.
- Counts:
  - `aphis_public_search_tool / awa_enforcement_action = 10`
  - `aphis_public_search_tool / awa_inspection_report = 25`
  - `ecfr / regulatory_citation_mapping = 1`
  - `federal_register / Rule = 1`

- Railway Bucket stores raw files under:
  - `sources/aphis_public_search_tool/`
  - `sources/ecfr/`
  - `sources/federal_register/`

- Missing metadata check is clean:
  - missing source_url = 0
  - missing storage_path = 0
  - missing content_hash = 0
  - missing file_size = 0

- Duplicate checks are clean:
  - duplicate canonical_key = 0
  - duplicate content_hash = 0
  - documents without canonical_key = 0

- Problem: `document_text_blocks` is still empty:
  - `SELECT COUNT(*) FROM document_text_blocks;` returns `0`

- Problem: APHIS Public Search Tool manually shows 29 inspection rows for Equitech-Bio Inc. certificate `74-B-0345`, but production has only 25 inspection reports total and only a partial subset for Equitech.
- Problem: APHIS enforcement saved 10 records, but repeated verification later may return `records_found=0` instead of finding the same 10 and skipping duplicates.

Main goal:
Fix production data-quality gaps after ingestion:

1. APHIS inspection pagination / record limit.
2. Text extraction into `document_text_blocks`.
3. APHIS enforcement repeated-run consistency.
4. Backward-compatible API naming for `source_type` / `source_subtype`.

Do not delete production data.
Do not wipe Railway Postgres.
Do not change Railway Bucket layout unless necessary.
Do not build frontend.
Do not add AI.
Do not add Neo4j.
Do not add Dagster.
Do not add Celery.

Task 1 — Fix APHIS inspection pagination / partial ingestion:

- Inspect `backend/app/services/ingestion/aphis_adapter.py` and any related APHIS scraping scripts.
- Remove hardcoded limits that stop at 25 records or only first visible rows.
- The scraper must paginate or scroll through all available APHIS inspection rows for the configured search.
- Manual APHIS check showed Equitech-Bio Inc. certificate `74-B-0345` has 29 rows in the official APHIS Public Search Tool.
- The ingestion response must report accurate:
  - `records_found`
  - `records_saved`
  - `duplicates_skipped`
  - `changed_records`
  - `errors`

- Add guardrails like `max_pages` or `max_rows` only as safety limits, not as a hidden production limit.
- If APHIS pagination cannot be fully solved in one pass, return clear errors/warnings instead of silently saving partial data.

Task 2 — Wire text extraction into ingestion:
Use existing table `document_text_blocks`.

Current schema has:

- `id`
- `source_document_id`
- `page_number`
- `block_index`
- `text`
- `confidence`
- `created_at`

Implement extraction for existing source types:

- PDF files:
  - Use a pure Python PDF text extraction library, preferably `pypdf`.
  - Extract text page by page.
  - Insert one or more text blocks per page.
  - Use `page_number` for PDF pages.
  - Use `confidence = 1.0` for normal embedded-text extraction.
  - If PDF text is empty, record an error/warning but do not crash ingestion.

- XML files:
  - Extract readable text from XML using Python standard library or safe parser.
  - Chunk into text blocks.
  - Use `page_number = 1`.
  - Use `confidence = 1.0`.

- JSON files:
  - Extract useful JSON text/fields or pretty-printed JSON.
  - Chunk into text blocks.
  - Use `page_number = 1`.
  - Use `confidence = 1.0`.

Important:

- Extraction must be idempotent.
- If a source document already has text blocks, do not insert duplicates.
- Extraction should run automatically after a new source document is saved.
- Also create a backfill path for existing 37 production documents.

Task 3 — Add storage read support if missing:

- If `storage_service.py` only supports saving raw bytes, add a safe `read_raw_bytes(storage_path)` function.
- It must support Railway Bucket/S3 storage paths and local storage.
- For Railway Bucket, use existing S3-compatible env vars:
  - `S3_ENDPOINT_URL`
  - `S3_BUCKET_NAME`
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`
  - `AWS_DEFAULT_REGION`

- If reading from storage fails, fallback to downloading from `source_url` only as a fallback and log that fallback clearly.

Task 4 — Add protected extraction backfill endpoint:
Create a backend endpoint like:

`POST /extraction/backfill/run`

Security:

- Require the same `x-api-key` / `INGESTION_API_KEY` protection used by ingestion endpoints.

Behavior:

- Find all `source_documents` without matching `document_text_blocks`.
- Extract text from raw stored file.
- Insert text blocks.
- Do not duplicate text blocks.
- Return JSON:

```json
{
  "status": "success",
  "documents_checked": 37,
  "documents_extracted": 37,
  "documents_skipped": 0,
  "text_blocks_created": 123,
  "errors": []
}
```

If some files fail extraction, endpoint should still complete and include errors array.

Task 5 — Add local script:
Create:

`backend/scripts/backfill_text_extraction.py`

It should:

- Use current database config.
- Run extraction backfill locally or against configured DB.
- Print:
  - documents_checked
  - documents_extracted
  - documents_skipped
  - text_blocks_created
  - errors

Task 6 — Fix APHIS enforcement repeated-run behavior:

- Inspect APHIS enforcement ingestion logic.
- Repeated production verification should rediscover the same enforcement records and return duplicates skipped.
- Expected second-pass behavior:
  - `records_found` should equal rediscovered enforcement records.
  - `records_saved = 0`
  - `duplicates_skipped > 0`

- If APHIS source page changes or is unavailable, return clear `errors`, not silent success with `records_found=0`.

Task 7 — Source type naming consistency:

- DB column is `source_type`.
- API/n8n sometimes returns `source_subtype`.
- Do not break current n8n workflow.
- Add backward-compatible responses that include both:
  - `source_type`
  - `source_subtype`

- They can contain the same value for now.
- Do not rename DB columns in this task.

Task 8 — Requirements:

- Add `pypdf` to `backend/requirements.txt` if not already present.
- Avoid heavy OCR dependencies for now.
- Do not install Tesseract/PaddleOCR in this task.
- First goal is embedded-text extraction and searchable text blocks.
- OCR fallback can be a later task.

Task 9 — Verification commands:
Run:

```powershell
cd backend
python -m compileall app scripts
```

If possible, run local smoke/backfill tests.

After implementation, update `backend/README.md` with:

- extraction flow
- backfill endpoint
- document_text_blocks verification SQL
- APHIS pagination note
- enforcement repeated-run behavior

Task 10 — Append/update `AGENT_HANDOFF.md`:
Include:

- files changed
- exact commands run
- outputs
- what was fixed
- what remains blocked
- how to verify after Railway deployment
- expected SQL after backfill:

```sql
SELECT COUNT(*) AS total_text_blocks FROM document_text_blocks;
```

Expected after backfill:

- should be greater than 0

Also include expected n8n/API test:

- POST `/extraction/backfill/run` with `x-api-key`
- then check `document_text_blocks`
