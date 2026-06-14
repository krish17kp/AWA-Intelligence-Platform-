# Backfill Testing

Assume the API is running at `http://localhost:8000`.

## Dry Run: Single State

```bash
curl -X POST http://localhost:8000/backfill/run \
  -H "Content-Type: application/json" \
  -d '{"source":"aphis_inspections","start_date":"2026-01-01","end_date":"2026-06-14","state_code":"CA","max_pages":1,"page_size":50,"dry_run":true}'
```

## Real Run: Single State

Keep `max_pages=1` for the first controlled write:

```bash
curl -X POST http://localhost:8000/backfill/run \
  -H "Content-Type: application/json" \
  -d '{"source":"aphis_inspections","start_date":"2026-01-01","end_date":"2026-06-14","state_code":"CA","max_pages":1,"page_size":50,"dry_run":false}'
```

## All-State Dry Run

```bash
curl -X POST http://localhost:8000/backfill/run \
  -H "Content-Type: application/json" \
  -d '{"source":"aphis_inspections","start_date":"2026-01-01","end_date":"2026-06-14","include_all_states":true,"max_pages":1,"page_size":50,"dry_run":true}'
```

This contacts APHIS once per configured state but does not preserve files or create source documents.

## All-State Real Run Safety

This request must return HTTP 400 with `All-state real backfill requires confirm_large_run=true.`:

```bash
curl -i -X POST http://localhost:8000/backfill/run \
  -H "Content-Type: application/json" \
  -d '{"source":"aphis_inspections","start_date":"2026-01-01","end_date":"2026-06-14","include_all_states":true,"max_pages":1,"dry_run":false,"confirm_large_run":false}'
```

A real all-state run requires both `dry_run=false` and `confirm_large_run=true`. Keep `max_pages` explicitly bounded.

## Check Coverage

```bash
curl http://localhost:8000/coverage
```

Review `states_attempted`, `date_ranges_attempted`, `total_records_by_state`, and `latest_coverage_snapshots`.

## Check Ingestion Events

Replace `RUN_ID` with the `run_id` returned by `/backfill/run`:

```bash
curl http://localhost:8000/ingestion/runs/RUN_ID/events
```

For skipped duplicates, verify the event payload includes `duplicate_of` and `matched_on`.

Do not claim full historical coverage until coverage snapshots prove all intended source/date/state ranges were completed.
