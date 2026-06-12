import json
from datetime import datetime, timezone

import requests

from app.services.hashing_service import sha256_bytes
from app.services.storage_service import save_raw_bytes


FEDERAL_REGISTER_DOCUMENTS_URL = "https://www.federalregister.gov/api/v1/documents.json"

APHIS_RELEVANT_AGENCIES = {
    "agricultural marketing service",
    "animal and plant health inspection service",
    "agriculture department",
    "food safety and inspection service",
}

APHIS_RELEVANT_TERMS = [
    "animal welfare act",
    "animal welfare",
    "aphis",
    "9 cfr",
    "9 c.f.r.",
    "animal care",
    "licensed",
    "registered",
    "exhibitor",
    "dealer",
    "research facility",
    "horse protection act",
    "animal fighting",
    "pet animal",
]


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
    raw_json = json.loads(raw_content.decode("utf-8"))

    all_results = raw_json.get("results", [])
    filtered = []
    for record in all_results:
        title_text = (record.get("title") or "").lower()
        abstract_text = (record.get("abstract") or "").lower()
        combined = f"{title_text} {abstract_text}"

        agency_names = {
            a.get("name", "").lower()
            for a in (record.get("agencies") or [])
        }

        is_aphis_relevant = bool(agency_names & APHIS_RELEVANT_AGENCIES) or any(
            term in combined for term in APHIS_RELEVANT_TERMS
        )
        if is_aphis_relevant:
            filtered.append(record)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = "federal_register_aphis_awa_" + timestamp + ".json"

    filter_result = {
        "total_results": len(all_results),
        "filtered_results": len(filtered),
        "results": filtered,
    }
    filter_content = json.dumps(filter_result, indent=2).encode("utf-8")
    filter_hash = sha256_bytes(filter_content)

    storage_path = save_raw_bytes(
        source_name="federal_register",
        filename=filename,
        content=filter_content,
    )

    return {
        "raw_json": filter_result,
        "content_hash": filter_hash,
        "storage_path": storage_path,
        "file_size_bytes": len(filter_content),
        "retrieved_at": datetime.now(timezone.utc),
    }