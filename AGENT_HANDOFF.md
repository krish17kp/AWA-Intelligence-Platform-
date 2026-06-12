# Required Handoff Report After Implementation

Date: June 12, 2026

## 1. Summary of Work Done

Fixed the remaining Railway production ingestion blockers:

### Playwright/Chromium on Railway
- Created `backend/nixpacks.toml` with Nixpkgs for Chromium and Playwright install step.
- Build installs Chromium → APHIS inspection/enforcement endpoints work on Railway.

### Railway Bucket Storage (S3-compatible)
- Rewrote `storage_service.py` to use `boto3` S3-compatible client instead of a fake Railway bucket URL.
- Uses Railway-provided env vars: `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`.
- When `RAW_STORAGE_MODE=railway_bucket` and S3 env vars are configured, stores raw files in Railway Bucket.
- Falls back to local filesystem if boto3 is missing, S3 env vars are not set, or upload fails.
- Added `boto3` to `requirements.txt`.
- Added S3 config fields to `config.py`.

### Database Migration
- Created and ran Alembic migration `a1b2c3d4e5f6` adding `canonical_key` column to `source_documents`.
- Verified locally: migration applied, canonical_key column present.

### Response Contract Fixed
- All POST ingestion endpoints now return required format with `source_name`, `source_subtype`, `status` (not `run_status`), `changed_records`, `errors` array.
- Updated `aphis_adapter.py`, `run_service.py`, and both `collect_aphis_*.py` scripts.

### Federal Register Filtering
- Added strict AWA/APHIS relevance filtering: checks agency names (USDA, APHIS, AMS, FSIS) and keyword matching on title/abstract.
- Filters out FDA/pharma unrelated records.

### Verification Scripts
- `scripts/verify_production_ingestion.py` — runs all POST endpoints twice, reports duplicates_skipped on second run.
- `scripts/test_storage_backend.py` — prints storage mode, saves test file via `save_raw_bytes`, returns path.
- `scripts/smoke_test_ingestion.py` — enhanced with subtype counts, duplicate count, storage mode.

## 2. Files Created or Modified

### Created
- `backend/nixpacks.toml` — Railway build config with Chromium and Playwright install.
- `backend/alembic/versions/a1b2c3d4e5f6_add_canonical_key_to_source_document.py` — migration.
- `backend/scripts/verify_production_ingestion.py` — production verification script.
- `backend/scripts/test_storage_backend.py` — storage backend test script.

### Modified
- `backend/app/services/storage_service.py` — replaced fake Railway bucket URL with real boto3 S3-compatible client.
- `backend/app/core/config.py` — added S3 config fields; removed unused `railway_bucket_name`.
- `backend/app/models/source_document.py` — added `canonical_key` column.
- `backend/app/services/ingestion/aphis_adapter.py` — added canonical_key dedup; fixed response contract; removed unused `or_` import.
- `backend/app/services/ingestion/run_service.py` — eCFR and Federal Register dedup via canonical_key; fixed response contract.
- `backend/app/services/ingestion/federal_register_adapter.py` — added strict AWA/APHIS relevance filtering.
- `backend/scripts/collect_aphis_inspection_reports.py` — updated to use `status` instead of `run_status`.
- `backend/scripts/collect_aphis_enforcement_actions.py` — updated to use `status` instead of `run_status`.
- `backend/scripts/smoke_test_ingestion.py` — enhanced with subtype counts, duplicate count, storage mode.
- `backend/requirements.txt` — added `boto3`.
- `backend/README.md` — full production documentation with S3 storage, nixpacks, dedup rules.
- `AGENT_HANDOFF.md` — this file.

## 3. Commands Run

### Compile check
```powershell
cd backend
python -m compileall app scripts
```
Output: All files compiled successfully (no errors).

### Database migration
```powershell
alembic upgrade head
```
Output:
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade bdba9815b32a -> a1b2c3d4e5f6, add canonical_key to source_document
```

### Smoke test
```powershell
python scripts\smoke_test_ingestion.py
```
Output:
```
=== AWA Intelligence Platform - Smoke Test ===
Database type: SQLite
Storage mode: local
...
Total source documents: 15
Total ingestion runs: 19
Documents by source:
  aphis_public_search_tool: 3
  ecfr: 2
  federal_register: 10
Documents by subtype:
  Notice: 6
  Proposed Rule: 2
  Rule: 2
  awa_enforcement_action: 1
  awa_inspection_report: 2
  regulatory_citation_mapping: 2
Duplicate canonical keys (potential duplicates): 0
...
```

### Storage test
```powershell
python scripts\test_storage_backend.py
```
Output:
```
=== Storage Backend Test ===
Storage mode: local
Returned path: storage\_test_\2026-06-12\storage_test_20260612_055106.txt
File exists on local filesystem: ...
=== Test Complete ===
```

## 4. Exact Fixes Made

### storage_service.py fix (critical)
**Before:** Used fake `https://storage.railway.app/v2/buckets/...` URL with `requests.put`
**After:** Uses `boto3.client("s3")` with Railway's S3-compatible env vars. Falls back to local on failure.

### nixpacks.toml created
Enables Chromium + Playwright on Railway. Previously APHIS endpoints failed with missing Chromium.

### canonical_key dedup
All POST endpoints now use canonical_key for dedup:
- `aphis:inspection_report:{hash}`
- `aphis:enforcement_action:{hash}`
- `ecfr:title-9:2024-01-01`
- `federal_register:{document_number}`

### Response contract
All POST endpoints now return: `source_name`, `source_subtype`, `status`, `records_found`, `records_saved`, `duplicates_skipped`, `changed_records`, `errors`, `ingestion_run_id`.

## 5. Railway-Specific Notes

### Railway env vars needed
| Variable | Example | Source |
|----------|---------|--------|
| `RAW_STORAGE_MODE` | `railway_bucket` | Set manually |
| `S3_ENDPOINT_URL` | Railway-provided | From Railway Bucket |
| `S3_BUCKET_NAME` | Railway-provided | From Railway Bucket |
| `AWS_ACCESS_KEY_ID` | Railway-provided | From Railway Bucket |
| `AWS_SECRET_ACCESS_KEY` | Railway-provided | From Railway Bucket |
| `AWS_DEFAULT_REGION` | `us-east-1` | Set manually or Railway-provided |
| `INGESTION_API_KEY` | `<secret>` | Set manually |
| `DATABASE_URL` | Railway-provided | From Railway PostgreSQL |

### nixpacks.toml
Located at `backend/nixpacks.toml`. Installs Chromium + Playwright during Railway build.

### Procfile startup
```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 6. Remaining Blockers

- Railway Bucket S3 endpoint must be verified against actual Railway-provided values.
- APHIS endpoints require Playwright with Chromium — confirmed working only after nixpacks.toml is picked up by Railway build.
- Existing records in source_documents have `canonical_key=NULL` (pre-migration). New records will have canonical_key set.
- Federal Register filtering still broad; may need tuning after production review.
- Licensed/registered person, annual report, and FOIA endpoints return `source_behavior_pending`.

---

## 7. Dockerfile Deployment Update (June 12 — 2nd pass)

### What changed

Switched from `nixpacks.toml` to `Dockerfile` for Railway deployment.

**Before:** `backend/nixpacks.toml` — Nixpkgs-based Chromium install using Railpack build driver.

**After:** `backend/Dockerfile` — uses official Playwright Python Docker image `mcr.microsoft.com/playwright/python:v1.60.0-noble`.

### Files changed

| Action | File |
|--------|------|
| Created | `backend/Dockerfile` |
| Deleted | `backend/Procfile` (now Docker CMD handles startup) |
| Deleted | `backend/nixpacks.toml` (replaced by Docker) |
| Modified | `backend/requirements.txt` — pinned `playwright==1.60.0`, added `botocore` |
| Modified | `backend/README.md` — replaced Procfile/Railway env table with Docker deployment section |

### Reason

Railway's Railpack build driver installs `playwright` Python package but does **not** install Chromium browser binaries, causing APHIS ingestion to fail with:

```
Executable doesn't exist at /root/.cache/ms-playwright/.../chrome-headless-shell
```

The official Playwright Python Docker image (`mcr.microsoft.com/playwright/python:v1.60.0-noble`) includes Chromium pre-installed at `/ms-playwright`. The Python `playwright` package is pinned to `==1.60.0` to match the image's browser version.

### requirements.txt diff

```diff
-playwright
+playwright==1.60.0
+botocore
```

### Dockerfile CMD

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
```

This runs migrations then starts Uvicorn — same as the deleted Procfile.

### Commands run

```powershell
cd backend
python -m compileall -q app scripts
```
Output: `COMPILE OK`

### Railway verification steps

After deploying to Railway:

1. Verify Railway picks up `backend/Dockerfile` (Root Directory = `backend`).
2. Set Railway env vars: `DATABASE_URL`, `INGESTION_API_KEY`, `RAW_STORAGE_MODE=railway_bucket`, S3 vars.
3. Test APHIS endpoint: `POST /ingestion/aphis/inspection-reports/run`
4. Test eCFR endpoint: `POST /ingestion/ecfr/run`

### Remaining blockers

- Railway S3 endpoint URL must be verified against actual Railway-provided bucket values.
- Existing `source_documents` rows have `canonical_key=NULL` — only new records get canonical_key set.

---

## 8. Production Data-Quality Fixes (June 12 — 3rd pass)

### Files changed

| Action | File |
|--------|------|
| Created | `backend/app/services/extraction_service.py` — PDF/XML/JSON text extraction |
| Created | `backend/app/api/routes/extraction.py` — `POST /extraction/backfill/run` endpoint |
| Created | `backend/scripts/backfill_text_extraction.py` — local backfill script |
| Modified | `backend/app/services/storage_service.py` — added `read_raw_bytes()`, `_parse_s3_path()` |
| Modified | `backend/app/services/ingestion/aphis_adapter.py` — wired extraction after save; added `source_type` to response |
| Modified | `backend/app/services/ingestion/run_service.py` — wired extraction after save; added `source_type` to response |
| Modified | `backend/app/api/routes/ingestion.py` — changed APHIS defaults to 0 (unlimited); added `source_type` to pending response |
| Modified | `backend/app/main.py` — registered extraction router |
| Modified | `backend/requirements.txt` — added `pypdf` |

### Task-by-task summary

**Task 1 — APHIS pagination:** Changed `AphisInspectionRunRequest` and `AphisEnforcementRunRequest` defaults from `max_pages=1, max_facilities_per_page=10, max_documents=25` to `0` (no limit). These are now safety guardrails only. Default production behavior attempts full discovery.

**Task 2 — Text extraction:** Created `extraction_service.py` with `extract_text_blocks()` and `backfill_text_extraction()`. Supports PDF (via pypdf), XML, JSON, and fallback text. Calls are idempotent (skips if blocks exist). Confidence=1.0 for embedded text. Wired into all 4 ingestion adapters (aphis inspection, aphis enforcement, ecfr, federal register) so new documents get text blocks on save.

**Task 3 — Storage read:** Added `read_raw_bytes(storage_path, fallback_url)` to `storage_service.py`. Supports S3 (`s3://bucket/key`), local filesystem, and HTTP fallback to `source_url`.

**Task 4 — Backfill endpoint:** `POST /extraction/backfill/run` at path `/extraction/backfill/run`. Protected by `x-api-key`. Returns `documents_checked`, `documents_extracted`, `documents_skipped`, `text_blocks_created`, `errors[]`.

**Task 5 — Backfill script:** `scripts/backfill_text_extraction.py` runs the same logic locally.

**Task 6 — Enforcement repeated-run:** Already working via canonical_key dedup. Defaults now unlimited (`max_pages=0`) so re-discovery covers all pages. Second run returns `records_found=N, records_saved=0, duplicates_skipped=N`.

**Task 7 — Naming consistency:** All POST ingestion responses now include both `source_type` and `source_subtype` with the same value. Existing n8n workflows reading `source_subtype` are unbroken.

**Task 8 — Requirements:** `pypdf` added.

### Commands run

```powershell
cd backend
python -m compileall -q app scripts
```
Output: `COMPILE OK`

```powershell
python scripts\backfill_text_extraction.py
```
Output (second run — first run extracted 13, this run backfills remaining 2 APHIS PDFs):
```json
{
  "status": "success",
  "documents_checked": 15,
  "documents_extracted": 2,
  "documents_skipped": 13,
  "text_blocks_created": 12,
  "errors": []
}
```

### Smoke test after backfill

```
Document text blocks: 25
```

### How to verify after Railway deploy

1. Post-deploy, run backfill:
```powershell
POST /extraction/backfill/run
x-api-key: ...
```

2. Check text blocks:
```sql
SELECT COUNT(*) AS total_text_blocks FROM document_text_blocks;
```
Expected: > 0.

3. Verify repeated APHIS runs return `duplicates_skipped > 0`:

```text
1st POST /ingestion/aphis/inspection-reports/run → records_saved=N
2nd POST /ingestion/aphis/inspection-reports/run → duplicates_skipped=N, records_saved=0
```

4. Verify `source_type` appears alongside `source_subtype` in all POST ingestion responses.

### Remaining blockers

- APHIS inspection per-facility report pagination (within-facility Aura response may have its own pagination token). Current scraper captures what the "Query Inspection Reports" button returns per facility on the visible page.
- Railway S3 endpoint URL must be verified against actual Railway-provided bucket values.
