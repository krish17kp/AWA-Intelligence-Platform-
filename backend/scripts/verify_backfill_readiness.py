import sys
from collections.abc import Iterable
from pathlib import Path

from sqlalchemy import inspect, text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.database import engine
from app.main import app


REQUIRED_TABLES = {
    "source_documents",
    "ingestion_runs",
    "ingestion_events",
    "coverage_snapshots",
    "document_text_blocks",
}

REQUIRED_ENDPOINTS = {
    ("POST", "/backfill/plan"),
    ("POST", "/backfill/run"),
    ("GET", "/coverage"),
    ("GET", "/ingestion/runs/{run_id}/events"),
}


def report(level: str, message: str) -> str:
    print(f"{level}: {message}")
    return level


def registered_endpoints() -> set[tuple[str, str]]:
    endpoints: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods: Iterable[str] = getattr(route, "methods", set()) or set()
        if not path:
            continue
        endpoints.update((method, path) for method in methods)
    return endpoints


def main() -> int:
    results: list[str] = []

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        results.append(report("PASS", "Database connection succeeded."))
    except Exception as error:
        results.append(report("FAIL", f"Database connection failed: {error}"))

    try:
        existing_tables = set(inspect(engine).get_table_names())
        missing_tables = sorted(REQUIRED_TABLES - existing_tables)
        if missing_tables:
            results.append(
                report(
                    "FAIL",
                    f"Required tables are missing: {', '.join(missing_tables)}",
                )
            )
        else:
            results.append(report("PASS", "All required backfill tables exist."))
    except Exception as error:
        results.append(report("FAIL", f"Could not inspect database tables: {error}"))

    endpoints = registered_endpoints()
    missing_endpoints = sorted(REQUIRED_ENDPOINTS - endpoints)
    if missing_endpoints:
        formatted = ", ".join(f"{method} {path}" for method, path in missing_endpoints)
        results.append(report("FAIL", f"Required endpoints are missing: {formatted}"))
    else:
        results.append(report("PASS", "Required backfill endpoints are registered."))

    storage_mode = settings.raw_storage_mode.strip().lower()
    storage_values = {
        "S3_ENDPOINT_URL": settings.s3_endpoint_url,
        "S3_BUCKET_NAME": settings.s3_bucket_name,
        "AWS_ACCESS_KEY_ID": settings.aws_access_key_id,
        "AWS_SECRET_ACCESS_KEY": settings.aws_secret_access_key,
    }
    missing_storage = [
        name for name, value in storage_values.items() if not value.strip()
    ]
    if storage_mode == "railway_bucket":
        if missing_storage:
            results.append(
                report(
                    "WARN",
                    "Railway bucket mode is selected but storage variables are "
                    f"missing: {', '.join(missing_storage)}",
                )
            )
        else:
            results.append(
                report(
                    "PASS",
                    "Railway/S3 bucket variables are present. Endpoint reachability "
                    "was not tested.",
                )
            )
    elif storage_mode == "local":
        results.append(
            report(
                "WARN",
                "Raw storage mode is local; Railway/S3 bucket readiness is not verified.",
            )
        )
        if missing_storage:
            results.append(
                report(
                    "WARN",
                    f"Optional Railway/S3 variables are missing: {', '.join(missing_storage)}",
                )
            )
    else:
        results.append(
            report(
                "WARN",
                f"Unknown RAW_STORAGE_MODE value: {settings.raw_storage_mode!r}",
            )
        )

    pass_count = results.count("PASS")
    warn_count = results.count("WARN")
    fail_count = results.count("FAIL")
    print(
        f"\nSUMMARY: PASS={pass_count} WARN={warn_count} FAIL={fail_count}"
    )
    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
