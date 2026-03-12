import asyncio
import hashlib
from pathlib import Path


async def calculate_file_hash(file_path: Path) -> str:
    """Асинхронно вычисляет SHA-256 хеш файла."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _calculate_file_hash, file_path)


def _calculate_file_hash(file_path: Path) -> str:
    """Синхронная версия вычисления хеша."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        for byte_block in iter(lambda: file_handle.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()
