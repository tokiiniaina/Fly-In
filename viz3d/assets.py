"""Paths and loading helpers for reusable Panda3D visual assets."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"
MODEL_ROOT = ASSET_ROOT / "models"
SPRITE_ROOT = ASSET_ROOT / "ui"
DRONE_MODEL = MODEL_ROOT / "drone.bam"
SKY_MODEL = MODEL_ROOT / "sky.bam"
MESAS_MODEL = MODEL_ROOT / "mesas.bam"


def _slug(value: str | None) -> str:
    """Make a stable filename part from a map color name."""
    if value is None or value == "none":
        return "default"
    return re.sub(r"[^a-z0-9_-]+", "_", value.lower())


def site_model_path(kind: str, color: str | None) -> Path:
    """Return the exported model path for one zone kind and color."""
    return MODEL_ROOT / f"site_{kind}_{_slug(color)}.bam"


def zone_sprite_path(kind: str) -> Path:
    """Return the PNG sprite path for one zone kind."""
    return SPRITE_ROOT / f"zone_{kind}.png"


def load_model(loader: Any, path: Path) -> Any:
    """Load a required BAM asset and report a clear error if it is invalid."""
    model = loader.loadModel(str(path))
    if model.isEmpty():
        raise RuntimeError(f"could not load visual asset: {path}")
    return model
