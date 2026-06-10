import json
from datetime import datetime, timezone

import requests

from app.services.hashing_service import sha256_bytes
from app.services.storage_service import save_raw_bytes


FEDERAL_REGISTER_DOCUMENTS_URL = "https://www.federalregister.gov/api/v1/documents.json"


def fetch_federal_register_animal_welfare_records(per_page: int = 5):
    params = {
        "conditions[term]": "animal welfare",
        "per_page": per_page,
        "order": "newest",
        "fields[]": [
            "document_number",
            "title",
            "type",
            "publication_date",
            "html_url",
            "pdf_url",
            "abstract",
            "agencies",
        ],
    }

    response = requests.get(
        FEDERAL_REGISTER_DOCUMENTS_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    raw_content = response.content
    content_hash = sha256_bytes(raw_content)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = "federal_register_animal_welfare_" + timestamp + ".json"

    storage_path = save_raw_bytes(
        source_name="federal_register",
        filename=filename,
        content=raw_content,
    )

    raw_json = json.loads(raw_content.decode("utf-8"))

    return {
        "raw_json": raw_json,
        "content_hash": content_hash,
        "storage_path": storage_path,
        "file_size_bytes": len(raw_content),
        "retrieved_at": datetime.now(timezone.utc),
    }