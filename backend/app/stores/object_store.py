from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    def put(self, key: str, data: bytes) -> str: ...
    def get(self, key: str) -> bytes: ...


class FakeObjectStore:
    """In-memory, used in tests."""

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        self._data[key] = data
        return key

    def get(self, key: str) -> bytes:
        return self._data[key]


class LocalDiskObjectStore:
    """Real-enough for a single-machine dev/demo deployment — writes to disk
    instead of requiring a MinIO/S3 service running. Swap for an S3-compatible
    client later if a multi-node deployment needs it."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def put(self, key: str, data: bytes) -> str:
        path = self.base_dir / key
        path.write_bytes(data)
        return str(path)

    def get(self, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()
