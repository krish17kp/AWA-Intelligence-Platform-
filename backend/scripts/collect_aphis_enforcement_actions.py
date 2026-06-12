import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.services.ingestion.aphis_adapter import ingest_enforcement_actions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect and preserve raw APHIS enforcement action PDFs."
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1,
        help="Table pages to collect. Use 0 for all available pages.",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        default=0,
        help="PDFs to preserve per run. Use 0 for all discovered PDFs.",
    )
    parser.add_argument("--headed", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db = SessionLocal()
    try:
        result = ingest_enforcement_actions(
            db=db,
            max_pages=args.max_pages,
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
