import hashlib
from pathlib import Path


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: str | Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def verify_checksum(path: str | Path, expected_sha256: str | None) -> bool:
    if not expected_sha256:
        return True
    return sha256_file(path) == expected_sha256
