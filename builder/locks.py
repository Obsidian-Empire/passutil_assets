import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from lock_types import BlobManifest, LockEntry, OrganizedLockFile

_LOCK = asyncio.Lock()


async def load_lock_file(lock_file: Path) -> Dict[str, LockEntry]:
    """Асинхронно загружает файл блокировки с хешами."""
    if not lock_file.exists():
        return {}

    async with _LOCK:
        with open(lock_file, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

    if isinstance(data, dict) and "files" in data:
        flat_hashes: Dict[str, LockEntry] = {}
        for folder_files in data["files"].values():
            if isinstance(folder_files, dict):
                flat_hashes.update(folder_files)
        return flat_hashes

    return data


async def save_lock_file(lock_file: Path, hashes: Dict[str, LockEntry]) -> None:
    """Асинхронно сохраняет файл блокировки с хешами."""
    organized_hashes: OrganizedLockFile = {
        "metadata": {
            "last_update": datetime.now().isoformat(),
            "total_files": len(hashes),
            "version": "1.0",
        },
        "files": {},
    }

    for file_path, file_data in hashes.items():
        folder = file_data.get("folder", "root")
        if folder not in organized_hashes["files"]:
            organized_hashes["files"][folder] = {}
        organized_hashes["files"][folder][file_path] = file_data

    async with _LOCK:
        with open(lock_file, "w", encoding="utf-8") as file_handle:
            json.dump(organized_hashes, file_handle, indent=4)


async def save_blob_lock(lock_file: Path, data: BlobManifest) -> None:
    async with _LOCK:
        with open(lock_file, "w", encoding="utf-8") as file_handle:
            json.dump(data, file_handle, indent=4)
