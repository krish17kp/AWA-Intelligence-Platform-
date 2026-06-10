from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings


def save_raw_bytes(source_name: str, filename: str, content: bytes) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    folder_path = Path(settings.raw_storage_root) / source_name / today
    folder_path.mkdir(parents=True, exist_ok=True)

    file_path = folder_path / filename
    file_path.write_bytes(content)

    return str(file_path)