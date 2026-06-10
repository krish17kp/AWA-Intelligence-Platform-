## Current Project Path

New project root:

```text
D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform
```

Backend path:

```text
D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\backend
```

Old project reference path:

```text
D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main
```

The old project folder is intentionally nested twice. Use the exact path above.

Before doing any code changes, verify these old files exist:

```text
D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\scraper.py

D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\pdf_utils.py

D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\ocr.py

D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\extractor.py

D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\pipeline.py

D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\models.py

D:\open paws intern\awa records data harvesting analysis platform\new\awa-intelligence-platform\old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\scheduler.py
```

If any of these files do not exist, stop and report the missing file. Do not guess.



## Exact Old Code to Inspect and Reuse

Inspect the old project files at the exact paths listed above.

Reuse/adapt these specific parts:

### Old `scraper.py`

File:

```text
old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\scraper.py
```

Known useful functions:

* `generate_hash_id(url: str)`
* `_download_with_retry(url, retries=3, timeout=15)`
* `scrape_state(state_code="TX", license_type=None, max_pages=0)`
* `check_and_download_new_pdfs(sync_type="nightly_incremental")`
* `scrape_enforcement_actions(max_pages=0)`
* `enrich_enforcement_pdfs(db, limit=50)`

Use these as reference for APHIS Playwright/Salesforce scraping and PDF discovery.

Do not copy old database insert logic directly. The new project must preserve raw source documents first in `source_documents`.

### Old `pdf_utils.py`

File:

```text
old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\pdf_utils.py
```

Known useful functions:

* `sha256_bytes(content: bytes)`
* `sha256_file(path)`
* `download_pdf_bytes(url, retries=3, timeout=15, min_size=1000)`
* `verify_checksum(path, expected_sha256)`

Reuse/adapt into the new project’s hashing/storage/download services.

### Old `ocr.py`

File:

```text
old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\ocr.py
```

Known useful function:

* `extract_text_from_pdf(pdf_path)`

Keep this for the next OCR pipeline stage. Do not make OCR mandatory for source ingestion success today.

### Old `extractor.py`

File:

```text
old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\extractor.py
```

Known useful function:

* `extract_data(text, filename)`

Use as reference for extracting:

* facility name
* inspection date
* customer/license/certificate number
* violations
* animal inventory fields

Do not force full extraction today unless raw APHIS PDFs are successfully preserved first.

### Old `pipeline.py`

File:

```text
old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\pipeline.py
```

Known useful functions:

* `download_inspection_pdf`
* `process_single_inspection`
* `process_batch`
* `process_all_pending`
* `process_local_pdfs`

Use only as design reference for:

```text
download PDF → preserve raw → OCR → extract → persist normalized data
```

Today’s required part is raw preservation + dedupe + metadata.

### Old `models.py`

File:

```text
old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\models.py
```

Known useful model references:

* `Facility`
* `Inspection`
* `Violation`
* `Inventory`
* `EnforcementAction`
* `AISummary`
* `LegalMemo`

Use these only as reference for the future AWA ontology. Do not blindly copy the whole old model into the new project today.

### Old `scheduler.py`

File:

```text
old\AWA-Records-Data-Harvesting-Analysis-Platform-main\AWA-Records-Data-Harvesting-Analysis-Platform-main\backend\app\services\scheduler.py
```

Known useful functions:

* `nightly_sync_job`
* `start_scheduler`
* `stop_scheduler`

Do not use APScheduler as the main scheduler. n8n will orchestrate ingestion. Use scheduler.py only to understand old timing/job logic.


