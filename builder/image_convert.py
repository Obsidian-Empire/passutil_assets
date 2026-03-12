import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from PIL import Image

from config import MAX_CONCURRENT_OPERATIONS, WEBP_SETTINGS
from hashing import calculate_file_hash
from lock_types import LockEntry

logger = logging.getLogger(__name__)


def _save_as_webp(
    input_path: Path, output_path: Path, settings: Dict[str, object]
) -> None:
    with Image.open(input_path) as image:
        image.save(output_path, "WEBP", **settings)


async def convert_image(
    input_path: Path,
    output_path: Path,
    settings: Dict[str, object],
    semaphore: asyncio.Semaphore,
) -> Optional[str]:
    """Асинхронно конвертирует PNG в WebP."""
    async with semaphore:
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, _save_as_webp, input_path, output_path, settings
            )
            return await calculate_file_hash(output_path)
        except Exception as exc:
            logger.error("Error converting %s: %s", input_path, exc)
            return None


async def process_file(
    png_file: Path,
    output_path: Path,
    conversion_hashes: Dict[str, LockEntry],
    base_input_path: Path,
    semaphore: asyncio.Semaphore,
    new_hashes: Dict[str, LockEntry],
) -> None:
    """Асинхронно обрабатывает отдельный файл."""
    relative_path = png_file.relative_to(base_input_path)
    webp_file = output_path / f"{png_file.stem}.webp"
    input_hash = await calculate_file_hash(png_file)

    hash_key = str(relative_path)
    folder_structure = str(relative_path.parent)
    folder_display = "root" if folder_structure == "." else folder_structure

    existing_entry = conversion_hashes.get(hash_key)
    if (
        existing_entry
        and input_hash == existing_entry.get("input_hash")
        and webp_file.exists()
    ):
        logger.info(
            "Skipping [%s] %s - already converted and unchanged",
            folder_display,
            png_file.name,
        )
        new_hashes[hash_key] = existing_entry
        return

    logger.info("Converting [%s] %s", folder_display, png_file.name)
    output_hash = await convert_image(
        png_file, webp_file, WEBP_SETTINGS, semaphore
    )

    if output_hash:
        new_hashes[hash_key] = {
            "input_hash": input_hash,
            "output_hash": output_hash,
            "folder": str(relative_path.parent),
            "original_name": png_file.name,
            "webp_name": webp_file.name,
            "last_conversion": datetime.now().isoformat(),
        }
        logger.info(
            "Successfully converted [%s] %s", folder_display, png_file.name
        )
    else:
        logger.error("Failed to convert [%s] %s", folder_display, png_file.name)


async def process_directory(
    input_path: Path,
    output_path: Path,
    conversion_hashes: Dict[str, LockEntry],
    base_input_path: Optional[Path] = None,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> Dict[str, LockEntry]:
    """Асинхронно обрабатывает директорию и все её поддиректории."""
    if base_input_path is None:
        base_input_path = input_path

    if semaphore is None:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)

    new_hashes: Dict[str, LockEntry] = {}
    output_path.mkdir(parents=True, exist_ok=True)

    file_tasks = []
    for png_file in input_path.glob("*.png"):
        file_tasks.append(
            process_file(
                png_file,
                output_path,
                conversion_hashes,
                base_input_path,
                semaphore,
                new_hashes,
            )
        )

    if file_tasks:
        await asyncio.gather(*file_tasks)

    subdir_tasks = []
    for subdir in input_path.iterdir():
        if subdir.is_dir():
            relative_subdir = subdir.relative_to(input_path)
            output_subdir = output_path / relative_subdir
            subdir_tasks.append(
                process_directory(
                    subdir,
                    output_subdir,
                    conversion_hashes,
                    base_input_path,
                    semaphore,
                )
            )

    if subdir_tasks:
        results = await asyncio.gather(*subdir_tasks)
        for result in results:
            new_hashes.update(result)

    return new_hashes
