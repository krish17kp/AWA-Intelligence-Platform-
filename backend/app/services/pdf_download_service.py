import logging
import time

import requests

logger = logging.getLogger(__name__)

PDF_DOWNLOAD_HEADERS = {
    "Accept": "application/pdf,application/octet-stream,*/*",
    "User-Agent": "AWA-Intelligence-Platform/0.1",
}


def download_pdf_bytes(
    url: str,
    retries: int = 3,
    timeout: int = 30,
    min_size: int = 1000,
) -> bytes:
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers=PDF_DOWNLOAD_HEADERS,
                allow_redirects=True,
            )
            response.raise_for_status()
            content = response.content

            if len(content) < min_size:
                raise ValueError(
                    f"Downloaded content is too small to be a PDF ({len(content)} bytes)"
                )
            if not content.lstrip().startswith(b"%PDF-"):
                raise ValueError("Downloaded content does not have a PDF signature")

            return content
        except (requests.RequestException, ValueError) as error:
            last_error = error
            logger.warning(
                "PDF download attempt %s/%s failed for %s: %s",
                attempt,
                retries,
                url,
                error,
            )
            if attempt < retries:
                time.sleep(attempt * 2)

    raise RuntimeError(f"Unable to download a valid PDF from {url}") from last_error
