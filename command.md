Fix missing ingestion API routes for Railway/n8n.

Current Railway result:
GET /ingestion/summary returns {"detail":"Not Found"}.

Tasks:

1. Create `backend/app/api/routes/ingestion.py`.
2. Add `router = APIRouter(prefix="/ingestion", tags=["ingestion"])`.
3. Add `GET /ingestion/summary` returning:
   - total_documents
   - total_ingestion_runs
   - documents_by_source
   - latest_ingestion_runs
   - storage_mode
4. Add POST endpoints:
   - `/ingestion/ecfr/run`
   - `/ingestion/federal-register/run`
   - `/ingestion/aphis/inspection-reports/run`
   - `/ingestion/aphis/enforcement-actions/run`
   - `/ingestion/aphis/licensed-registered-persons/run`
   - `/ingestion/aphis/annual-reports/run`
   - `/ingestion/foia/logs/run`
5. Sources without implemented behavior must return truthful
   `source_behavior_pending` JSON with zero counts, no errors, and a null
   ingestion run ID.
6. Connect implemented endpoints to existing APHIS, eCFR, and Federal Register
   ingestion logic.
7. Protect every POST endpoint with `x-api-key` compared to
   `settings.ingestion_api_key`.
8. Add `ingestion_api_key` to config if missing.
9. Register the ingestion router in `app/main.py`.
10. Create and register `backend/app/api/routes/maintenance.py`.
11. Add `POST /maintenance/dedupe-source-documents`.
12. Run `python -m compileall app`.
13. Commit and push.

Do not build frontend, AI, Neo4j, Dagster, or Celery.

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
