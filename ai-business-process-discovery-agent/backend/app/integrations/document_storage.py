from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import UploadFile


class FileTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class StoredFile:
    key: str
    size_bytes: int


class DocumentStorage(Protocol):
    async def save(
        self,
        file: UploadFile,
        *,
        extension: str,
        max_size_bytes: int,
    ) -> StoredFile: ...

    async def delete(self, key: str) -> None: ...


class LocalDocumentStorage:
    """Local implementation of the replaceable document storage boundary."""

    _chunk_size = 1024 * 1024

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    async def save(
        self,
        file: UploadFile,
        *,
        extension: str,
        max_size_bytes: int,
    ) -> StoredFile:
        await asyncio.to_thread(self._root.mkdir, parents=True, exist_ok=True)
        key = f"{uuid4()}{extension}"
        destination = self._path_for(key)
        size = 0

        try:
            with destination.open("xb") as output:
                while chunk := await file.read(self._chunk_size):
                    size += len(chunk)
                    if size > max_size_bytes:
                        raise FileTooLargeError
                    await asyncio.to_thread(output.write, chunk)
        except Exception:
            await asyncio.to_thread(destination.unlink, missing_ok=True)
            raise
        finally:
            await file.close()

        return StoredFile(key=key, size_bytes=size)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path_for(key).unlink, missing_ok=True)

    def _path_for(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if path.parent != self._root:
            raise ValueError("Invalid storage key")
        return path
