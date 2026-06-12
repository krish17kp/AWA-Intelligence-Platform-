import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.services.ingestion.aphis_adapter import ingest_inspection_reports


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect and preserve raw APHIS AWA inspection report PDFs."
    )
    parser.add_argument("--state", default="TX", help="Two-letter state code.")
    parser.add_argument("--license-type", default=None)
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Pages to collect. Use 0 for all available pages.",
    )
    parser.add_argument(
        "--max-facilities-per-page",
        type=int,
        default=0,
        help="Facility query buttons per page. Use 0 for all facilities.",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=0,
        help="PDFs to preserve per run. Use 0 for all discovered PDFs.",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the Chromium browser while collecting.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    try:
        result = ingest_inspection_reports(
            db=db,
            state_code=args.state,
            license_type=args.license_type,
            max_pages=args.max_pages,
            max_facilities_per_page=args.max_facilities_per_page,
            max_documents=args.max_documents,
            headless=not args.headed,
        )
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "success" else 2
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, indent=2))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
