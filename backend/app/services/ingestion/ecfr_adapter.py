from datetime import datetime, timezone

import requests

from app.services.hashing_service import sha256_bytes
from app.services.storage_service import save_raw_bytes


ECFR_VERSIONER_URL = "https://www.ecfr.gov/api/versioner/v1/full/2024-01-01/title-9.xml"


def fetch_ecfr_title_9_sample():
    response = requests.get(
        ECFR_VERSIONER_URL,
        timeout=30,
        headers={
            "Accept": "application/xml,text/xml,*/*",
            "User-Agent": "AWA-Intelligence-Platform/0.1",
        },
    )

    response.raise_for_status()

    raw_content = response.content
    content_hash = sha256_bytes(raw_content)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = "ecfr_title_9_sample_" + timestamp + ".xml"

    storage_path = save_raw_bytes(
        source_name="ecfr",
        filename=filename,
        content=raw_content,
    )

    return {
        "content_hash": content_hash,
        "storage_path": storage_path,
        "file_size_bytes": len(raw_content),
        "retrieved_at": datetime.now(timezone.utc),
        "source_url": ECFR_VERSIONER_URL,
    }