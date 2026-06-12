import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import SessionLocal
from app.services.extraction_service import backfill_text_extraction


def main():
    db = SessionLocal()
    try:
        result = backfill_text_extraction(db)
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "success" else 1
    except Exception as error:
        print(json.dumps({"status": "failed", "error": str(error)}, indent=2))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())