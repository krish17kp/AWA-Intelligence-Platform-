import argparse
import json
import sys
import urllib.request
import urllib.error


def req(method: str, url: str, headers: dict | None = None) -> tuple[int, dict]:
    data = None if method == "GET" else b""
    req_obj = urllib.request.Request(url, data=data, method=method)
    if headers:
        for k, v in headers.items():
            req_obj.add_header(k, v)
    req_obj.add_header("Accept", "application/json")
    try:
        with urllib.request.urlopen(req_obj, timeout=30) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode()) if e.headers.get("Content-Type", "").startswith("application/json") else {"detail": str(e)}
        return e.code, body


def main():
    parser = argparse.ArgumentParser(
        description="Verify production ingestion endpoints on Railway."
    )
    parser.add_argument("--base-url", default="https://awa-intelligence-platform-production.up.railway.app")
    parser.add_argument("--api-key", required=True)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    headers = {"x-api-key": args.api_key}

    endpoints = [
        ("GET", "/ingestion/summary", None),
        ("POST", "/ingestion/aphis/inspection-reports/run", headers),
        ("POST", "/ingestion/aphis/enforcement-actions/run", headers),
        ("POST", "/ingestion/ecfr/run", headers),
        ("POST", "/ingestion/federal-register/run", headers),
    ]

    results = {}
    for method, path, hdrs in endpoints:
        label = f"{method} {path}"
        status, body = req(method, f"{base}{path}", hdrs)
        results[label] = {"status": status, "body": body}
        print(f"{status} {label}")

    print("\n--- Second run (should show duplicates_skipped) ---")
    for method, path, hdrs in endpoints:
        if method == "GET":
            continue
        label = f"{method} {path}"
        status, body = req(method, f"{base}{path}", hdrs)
        print(f"{status} {label}")
        dup = body.get("duplicates_skipped", "N/A")
        print(f"  duplicates_skipped={dup}, records_saved={body.get('records_saved')}")

    print("\n--- Final summary ---")
    _, summary = req("GET", f"{base}/ingestion/summary")
    print(json.dumps(summary, indent=2))
    print("\nDone.")


if __name__ == "__main__":
    main()
