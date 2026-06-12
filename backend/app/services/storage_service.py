import logging
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_storage_mode() -> str:
    mode = settings.raw_storage_mode.lower().strip()
    return mode if mode in ("railway_bucket", "local") else "local"


def save_raw_bytes(source_name: str, filename: str, content: bytes) -> str:
    mode = _get_storage_mode()

    if mode == "railway_bucket":
        return _save_to_s3_bucket(source_name, filename, content)

    return _save_local(source_name, filename, content)


def _save_to_s3_bucket(source_name: str, filename: str, content: bytes) -> str:
    try:
        import boto3
    except ImportError:
        logger.warning("boto3 not available, falling back to local storage")
        return _save_local(source_name, filename, content)

    endpoint_url = settings.s3_endpoint_url
    bucket_name = settings.s3_bucket_name
    access_key = settings.aws_access_key_id
    secret_key = settings.aws_secret_access_key
    region = settings.aws_default_region

    if not all([endpoint_url, bucket_name, access_key, secret_key]):
        logger.warning(
            "S3 env vars not fully configured (S3_ENDPOINT_URL, S3_BUCKET_NAME, "
            "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY), falling back to local storage"
        )
        return _save_local(source_name, filename, content)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    key = f"sources/{source_name}/{today}/{filename}"

    try:
        client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region or "us-east-1",
        )
        client.put_object(Bucket=bucket_name, Key=key, Body=content)
        return f"s3://{bucket_name}/{key}"
    except Exception as exc:
        logger.warning("S3 upload failed (%s), falling back to local storage", exc)
        return _save_local(source_name, filename, content)


def _save_local(source_name: str, filename: str, content: bytes) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    folder_path = Path(settings.raw_storage_root) / source_name / today
    folder_path.mkdir(parents=True, exist_ok=True)

    file_path = folder_path / filename
    file_path.write_bytes(content)

    return str(file_path)


def _parse_s3_path(storage_path: str) -> tuple[str, str] | None:
    if not storage_path.startswith("s3://"):
        return None
    without_prefix = storage_path[5:]
    slash_idx = without_prefix.find("/")
    if slash_idx == -1:
        return None
    bucket = without_prefix[:slash_idx]
    key = without_prefix[slash_idx + 1:]
    return bucket, key


def read_raw_bytes(storage_path: str, fallback_url: str | None = None) -> bytes | None:
    if storage_path.startswith("s3://"):
        parsed = _parse_s3_path(storage_path)
        if parsed:
            bucket, key = parsed
            try:
                import boto3
                client = boto3.client(
                    "s3",
                    endpoint_url=settings.s3_endpoint_url,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_default_region or "us-east-1",
                )
                obj = client.get_object(Bucket=bucket, Key=key)
                return obj["Body"].read()
            except Exception as exc:
                logger.warning("S3 read failed for %s: %s", storage_path, exc)

    local = Path(storage_path)
    if local.exists():
        return local.read_bytes()

    if fallback_url:
        try:
            import requests
            resp = requests.get(fallback_url, timeout=30)
            resp.raise_for_status()
            logger.info("Fell back to downloading from %s", fallback_url)
            return resp.content
        except Exception as exc:
            logger.warning("Fallback download failed for %s: %s", fallback_url, exc)

    return None
