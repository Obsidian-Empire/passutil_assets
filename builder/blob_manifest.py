from pathlib import Path
from typing import List

from config import ASSET_SECTIONS
from lock_types import BlobManifest, BlobPartItem


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


def _build_blob_part(
    base_url: str, section: str, part_dir: Path
) -> List[BlobPartItem]:
    part_items: List[BlobPartItem] = []
    for webp_file in sorted(part_dir.glob("*.webp"), key=lambda path: path.name):
        part_items.append(
            {
                "name": webp_file.stem,
                "url": f"{base_url}/{section}/{part_dir.name}/{webp_file.name}",
            }
        )
    return part_items


def build_blob_lock(output_path: Path, base_url: str) -> BlobManifest:
    normalized_base_url = _normalize_base_url(base_url)
    blob_lock: BlobManifest = {}

    for section in sorted(ASSET_SECTIONS):
        section_dir = output_path / section
        items = []

        if section_dir.exists() and section_dir.is_dir():
            for part_dir in sorted(
                [directory for directory in section_dir.iterdir() if directory.is_dir()],
                key=lambda path: path.name,
            ):
                part_items = _build_blob_part(
                    normalized_base_url, section, part_dir
                )
                items.append({"type": part_dir.name, "part": part_items})

        blob_lock[section] = {"items": items}

    return blob_lock
