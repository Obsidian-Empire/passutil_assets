import asyncio
import logging
from pathlib import Path

from blob_manifest import build_blob_lock
from image_convert import process_directory
from locks import load_lock_file, save_blob_lock, save_lock_file

logger = logging.getLogger(__name__)


async def async_main(input_dir: str, output_dir: str, base_url: str) -> None:
    """Асинхронная основная функция."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    lock_file = output_path / "conversion.lock"
    blob_lock_file = output_path / "blob.json"

    output_path.mkdir(parents=True, exist_ok=True)
    conversion_hashes = await load_lock_file(lock_file)
    new_hashes = await process_directory(
        input_path, output_path, conversion_hashes
    )
    await save_lock_file(lock_file, new_hashes)
    blob_lock = build_blob_lock(output_path, base_url)
    await save_blob_lock(blob_lock_file, blob_lock)
    logger.info("Conversion process completed!")


def main(input_dir: str, output_dir: str, base_url: str) -> None:
    """Точка входа для синхронного запуска."""
    asyncio.run(async_main(input_dir, output_dir, base_url))
