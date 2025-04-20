import argparse
import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Оптимальные настройки для конвертации
WEBP_SETTINGS = {
    "quality": 85,
    "method": 6,
    "lossless": False,
    "exact": True,
    "minimize_size": True,
    "alpha_quality": 90,
}

# Семафор для ограничения количества одновременных операций
MAX_CONCURRENT_OPERATIONS = 5


async def calculate_file_hash(file_path: Path) -> str:
    """Асинхронно вычисляет SHA-256 хеш файла."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _calculate_file_hash, file_path)


def _calculate_file_hash(file_path: Path) -> str:
    """Синхронная версия вычисления хеша."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


async def load_lock_file(lock_file: Path) -> Dict[str, Dict[str, str]]:
    """Асинхронно загружает файл блокировки с хешами."""
    if lock_file.exists():
        async with asyncio.Lock():
            with open(lock_file, "r") as f:
                data = json.load(f)
                if "files" in data:
                    flat_hashes = {}
                    for folder_files in data["files"].values():
                        flat_hashes.update(folder_files)
                    return flat_hashes
                return data
    return {}


async def save_lock_file(
    lock_file: Path, hashes: Dict[str, Dict[str, str]]
) -> None:
    """Асинхронно сохраняет файл блокировки с хешами."""
    organized_hashes = {
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

    async with asyncio.Lock():
        with open(lock_file, "w") as f:
            json.dump(organized_hashes, f, indent=4)


async def convert_image(
    input_path: Path,
    output_path: Path,
    settings: Dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> Optional[str]:
    """Асинхронно конвертирует PNG в WebP."""
    async with semaphore:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: Image.open(input_path).save(
                    output_path, "WEBP", **settings
                ),
            )
            return await calculate_file_hash(output_path)
        except Exception as e:
            logger.error(f"Error converting {input_path}: {e}")
            return None


async def process_file(
    png_file: Path,
    output_path: Path,
    conversion_hashes: Dict[str, Dict[str, str]],
    base_input_path: Path,
    semaphore: asyncio.Semaphore,
    new_hashes: Dict[str, Dict[str, str]],
) -> None:
    """Асинхронно обрабатывает отдельный файл."""
    relative_path = png_file.relative_to(base_input_path)
    webp_file = output_path / f"{png_file.stem}.webp"
    input_hash = await calculate_file_hash(png_file)

    hash_key = str(relative_path)
    folder_structure = str(relative_path.parent)
    folder_display = "root" if folder_structure == "." else folder_structure

    if (
        hash_key in conversion_hashes
        and input_hash == conversion_hashes[hash_key]["input_hash"]
        and webp_file.exists()
    ):
        logger.info(
            f"Skipping [{folder_display}] {png_file.name} - already converted and unchanged"
        )
        new_hashes[hash_key] = conversion_hashes[hash_key]
        return

    logger.info(f"Converting [{folder_display}] {png_file.name}")
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
            f"Successfully converted [{folder_display}] {png_file.name}"
        )
    else:
        logger.error(f"Failed to convert [{folder_display}] {png_file.name}")


async def process_directory(
    input_path: Path,
    output_path: Path,
    conversion_hashes: Dict[str, Dict[str, str]],
    base_input_path: Optional[Path] = None,
) -> Dict[str, Dict[str, str]]:
    """Асинхронно обрабатывает директорию и все её поддиректории."""
    if base_input_path is None:
        base_input_path = input_path

    new_hashes: Dict[str, Dict[str, str]] = {}
    output_path.mkdir(parents=True, exist_ok=True)

    # Создаем семафор для ограничения одновременных операций
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_OPERATIONS)

    # Собираем все задачи для обработки файлов
    tasks = []
    for png_file in input_path.glob("*.png"):
        task = process_file(
            png_file,
            output_path,
            conversion_hashes,
            base_input_path,
            semaphore,
            new_hashes,
        )
        tasks.append(task)

    # Собираем задачи для поддиректорий
    for subdir in input_path.iterdir():
        if subdir.is_dir():
            relative_subdir = subdir.relative_to(input_path)
            output_subdir = output_path / relative_subdir
            subdir_task = process_directory(
                subdir, output_subdir, conversion_hashes, base_input_path
            )
            tasks.append(subdir_task)

    # Запускаем все задачи параллельно
    results = await asyncio.gather(*tasks)

    # Обновляем хеши из результатов поддиректорий
    for result in results:
        if isinstance(result, dict):
            new_hashes.update(result)

    return new_hashes


async def async_main(input_dir: str, output_dir: str) -> None:
    """Асинхронная основная функция."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    lock_file = output_path / "conversion.lock"

    output_path.mkdir(parents=True, exist_ok=True)
    conversion_hashes = await load_lock_file(lock_file)
    new_hashes = await process_directory(
        input_path, output_path, conversion_hashes
    )
    await save_lock_file(lock_file, new_hashes)
    logger.info("Conversion process completed!")


def main(input_dir: str, output_dir: str) -> None:
    """Точка входа для синхронного запуска."""
    asyncio.run(async_main(input_dir, output_dir))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert PNG images to WebP format"
    )
    parser.add_argument(
        "input_dir", help="Input directory containing PNG files"
    )
    parser.add_argument("output_dir", help="Output directory for WebP files")

    args = parser.parse_args()
    main(args.input_dir, args.output_dir)
