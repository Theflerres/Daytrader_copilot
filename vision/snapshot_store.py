"""
Organização hierárquica de snapshots para dataset / replay:
data/snapshots/YYYY-MM-DD/HH/<kind>/...
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Mapeia nome lógico da região do perfil -> pasta sob HH/
REGION_FOLDER = {
    "main_chart": "chart",
    "chart": "chart",
    "volume": "volume",
    "tape": "tape",
    "book": "book",
    "clock": "clock",
    "position_area": "position",
    "composite": "composite",
}


@dataclass
class SnapshotSession:
    """Uma sessão de gravação por ciclo (timestamp único)."""

    base_snapshots_dir: Path
    now: datetime
    stamp: str = field(init=False)

    def __post_init__(self) -> None:
        self.stamp = self.now.strftime("%Y%m%d_%H%M%S")

    def hour_root(self) -> Path:
        d = self.now.strftime("%Y-%m-%d")
        h = self.now.strftime("%H")
        return self.base_snapshots_dir / d / h

    def folder_for_region_key(self, region_key: str) -> Path:
        sub = REGION_FOLDER.get(region_key, region_key)
        p = self.hour_root() / sub
        p.mkdir(parents=True, exist_ok=True)
        return p

    def write_raw_png(self, region_key: str, png_bytes: bytes) -> Path:
        folder = self.folder_for_region_key(region_key)
        path = folder / f"raw_{self.stamp}.png"
        path.write_bytes(png_bytes)
        return path

    def write_processed_png(self, region_key: str, png_bytes: bytes, suffix: str = "processed") -> Path:
        folder = self.folder_for_region_key(region_key)
        path = folder / f"{suffix}_{self.stamp}.png"
        path.write_bytes(png_bytes)
        return path

    def write_composite(self, png_bytes: bytes) -> Path:
        return self.write_raw_png("composite", png_bytes)

    def write_metadata(self, payload: dict[str, Any]) -> Path:
        folder = self.hour_root()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"meta_{self.stamp}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def write_analysis_sidecar(self, text: str) -> Path:
        folder = self.hour_root()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"analysis_{self.stamp}.txt"
        path.write_text(text, encoding="utf-8")
        return path
