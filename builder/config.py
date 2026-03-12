from typing import Any, Dict, List

WEBP_SETTINGS: Dict[str, Any] = {
    "quality": 85,
    "method": 6,
    "lossless": False,
    "exact": True,
    "minimize_size": True,
    "alpha_quality": 90,
}

MAX_CONCURRENT_OPERATIONS = 4

ASSET_SECTIONS: List[str] = ["backgrounds", "badges", "banners", "frames"]
