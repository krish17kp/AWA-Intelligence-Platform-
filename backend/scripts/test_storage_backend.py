import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.services.storage_service import save_raw_bytes


def main():
    print("=== Storage Backend Test ===")
    print(f"Storage mode: {settings.raw_storage_mode}")

    test_content = (
        f"Test file created at {datetime.now(timezone.utc).isoformat()}\n"
        "AWA Intelligence Platform storage backend verification."
    ).encode("utf-8")

    result_path = save_raw_bytes(
        source_name="_test_",
        filename=f"storage_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt",
        content=test_content,
    )

    print(f"Returned path: {result_path}")

    if settings.raw_storage_mode == "local":
        resolved = Path(result_path)
        if resolved.exists():
            print(f"File exists on local filesystem: {resolved}")
            print(f"Content: {resolved.read_bytes().decode()}")
        else:
            print(f"WARNING: File not found at {resolved}")
    elif settings.raw_storage_mode == "railway_bucket":
        if result_path.startswith("s3://"):
            print("Storage is using S3-compatible bucket (Railway Bucket)")
            print(f"S3 path: {result_path}")
            print(f"Endpoint: {settings.s3_endpoint_url}")
            print(f"Bucket: {settings.s3_bucket_name}")
        elif result_path.startswith("storage") or result_path.startswith(str(Path("storage/raw"))):
            print("S3 bucket unavailable, fell back to local storage")
            resolved = Path(result_path)
            if resolved.exists():
                print(f"Local fallback file: {resolved}")
        else:
            print(f"Unknown storage path format: {result_path}")

    print()
    print("=== Test Complete ===")


if __name__ == "__main__":
    main()
