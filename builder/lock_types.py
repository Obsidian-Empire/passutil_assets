from typing import Dict, List, TypedDict


class LockEntry(TypedDict):
    input_hash: str
    output_hash: str
    folder: str
    original_name: str
    webp_name: str
    last_conversion: str


class LockMetadata(TypedDict):
    last_update: str
    total_files: int
    version: str


class OrganizedLockFile(TypedDict):
    metadata: LockMetadata
    files: Dict[str, Dict[str, LockEntry]]


class BlobPartItem(TypedDict):
    name: str
    url: str


class BlobPart(TypedDict):
    type: str
    part: List[BlobPartItem]


class BlobSection(TypedDict):
    items: List[BlobPart]


BlobManifest = Dict[str, BlobSection]
