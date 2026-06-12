Before making any changes, read `command.md` fully.

Fix the remaining Railway production ingestion blockers.

Current status:

- Railway backend is deployed.
- `/ingestion/summary` works.
- n8n can reach Railway backend.
- Dedupe endpoint worked after API key setup.
- APHIS ingestion fails on Railway because Playwright Chromium is missing.
- AGENT_HANDOFF.md says Railway Bucket endpoint was assumed, so bucket storage must be verified/fixed.
- Need production ingestion to save raw files into Railway Bucket and metadata into Railway PostgreSQL.

Tasks:

1. Fix Playwright/Chromium on Railway.
   - Ensure `playwright` is in `requirements.txt`.
   - Add proper Railway/Nixpacks setup so Chromium is installed during build, not at runtime.
   - Create/update `backend/nixpacks.toml` if needed.
   - Do not make buildCommand and startCommand the same.
   - Railway start command should remain:
     `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

2. Fix Railway Bucket storage implementation.
   - Do not use an assumed fake Railway bucket URL.
   - Use Railway Bucket’s S3-compatible variables:
     `S3_ENDPOINT_URL`
     `S3_BUCKET_NAME`
     `AWS_ACCESS_KEY_ID`
     `AWS_SECRET_ACCESS_KEY`
     `AWS_DEFAULT_REGION`
   - Use `boto3`/S3-compatible client for uploads.
   - Raw files must be stored in Railway Bucket when `RAW_STORAGE_MODE=railway_bucket`.
   - Local storage should remain only as development fallback.

3. Verify database migration.
   - Ensure `canonical_key` migration runs through Alembic.
   - Ensure Railway Postgres has required tables and columns.

4. Ensure ingestion endpoints work:
   - `POST /ingestion/ecfr/run`
   - `POST /ingestion/federal-register/run`
   - `POST /ingestion/aphis/inspection-reports/run`
   - `POST /ingestion/aphis/enforcement-actions/run`
   - `POST /maintenance/dedupe-source-documents`
   - `GET /ingestion/summary`

5. Add/verify production test scripts:
   - `scripts/test_storage_backend.py`
   - `scripts/verify_production_ingestion.py`

6. After changes, run:
   - `python -m compileall app scripts`
   - `python scripts/smoke_test_ingestion.py`

7. Commit and push changes.

8. Append/update `AGENT_HANDOFF.md` with:
   - files changed
   - exact fixes made
   - commands run
   - outputs
   - Railway-specific notes
   - remaining blockers if any

Do not build frontend.
Do not add AI.
Do not add Neo4j, Dagster, or Celery.
Do not change project scope.
Focus only on Railway Playwright, Railway Bucket storage, migrations, and production ingestion readiness.
