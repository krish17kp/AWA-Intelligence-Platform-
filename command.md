Fix the missing ingestion API routes for Railway/n8n.

Current issue:
GET /ingestion/summary returns 404 on Railway.
GET /ingestion-runs works only after DB migrations.

Tasks:

1. Create backend/app/api/routes/ingestion.py.
2. Add GET /ingestion/summary.
3. Add POST endpoints:
   - /ingestion/ecfr/run
   - /ingestion/federal-register/run
   - /ingestion/aphis/inspection-reports/run
   - /ingestion/aphis/enforcement-actions/run
   - /ingestion/aphis/licensed-registered-persons/run
   - /ingestion/aphis/annual-reports/run
   - /ingestion/foia/logs/run
4. Protect all POST ingestion endpoints with x-api-key using INGESTION_API_KEY.
5. Register ingestion router in app/main.py.
6. Add maintenance route:
   - POST /maintenance/dedupe-source-documents
7. Register maintenance router in app/main.py.
8. GET /ingestion/summary should return:
   - total_documents
   - total_ingestion_runs
   - documents_by_source
   - latest_ingestion_runs
   - storage_mode
9. Make sure the app starts on Railway.
10. Do not build frontend, AI, Neo4j, Dagster, or Celery.

After changes:

- commit
- push
- Railway redeploys

## Required Handoff Report After Implementation

After completing every implementation, create or update:

```text
AGENT_HANDOFF.md
```

The report must include:

1. Summary of Work Done
2. Files Created or Modified
3. Commands Run
4. Command Outputs for:
   - `python scripts\create_local_tables.py`
   - `python scripts\show_data_sources.py`
   - `python scripts\collect_ecfr_sample.py`
   - `python scripts\collect_federal_register_sample.py`
   - `python scripts\smoke_test_ingestion.py`
5. API Verification for:
   - `http://127.0.0.1:8000/health`
   - `http://127.0.0.1:8000/documents`
   - `http://127.0.0.1:8000/ingestion-runs`
   - `http://127.0.0.1:8000/documents/1`
6. Errors or Failed Items
7. Remaining Work
8. Supabase Readiness
