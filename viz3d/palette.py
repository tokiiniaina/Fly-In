"""Sunset voxel palette shared by the whole scene."""

from __future__ import annotations

import colorsys
import zlib
from typing import Dict, Tuple

RGB = Tuple[float, float, float]
UNIT = 1.5

ORANGE: RGB = (0.98, 0.58, 0.10)
ORANGE_DK: RGB = (0.80, 0.42, 0.08)
YELLOW: RGB = (1.00, 0.78, 0.20)
GREY: RGB = (0.54, 0.56, 0.60)
GREY_DK: RGB = (0.20, 0.21, 0.26)
GREY_LT: RGB = (0.72, 0.74, 0.78)
DARK: RGB = (0.12, 0.11, 0.18)
DARK2: RGB = (0.20, 0.17, 0.27)
GLASS: RGB = (0.07, 0.10, 0.18)
CYAN: RGB = (0.35, 0.85, 1.00)
BLUE: RGB = (0.30, 0.62, 1.00)
RED: RGB = (0.92, 0.16, 0.22)
EMBER: RGB = (1.00, 0.36, 0.20)
GREEN: RGB = (0.30, 0.95, 0.45)
TEAL: RGB = (0.18, 0.78, 0.72)
WHITE: RGB = (0.95, 0.92, 0.84)
CACTUS: RGB = (0.22, 0.62, 0.28)

SAND_A: RGB = (0.94, 0.63, 0.22)
SAND_B: RGB = (0.99, 0.73, 0.30)
SAND_C: RGB = (0.86, 0.50, 0.20)
SAND_D: RGB = (0.78, 0.44, 0.19)
STRATA = [(0.82, 0.47, 0.20), (0.70, 0.39, 0.18), (0.60, 0.33, 0.17),
          (0.50, 0.28, 0.16), (0.42, 0.23, 0.15)]

PAD_DEFAULT: Dict[str, RGB] = {
    "start": (0.20, 0.78, 0.50), "end": (1.00, 0.80, 0.22),
    "normal": (0.25, 0.50, 0.98), "priority": (0.30, 0.88, 0.42),
    "restricted": (0.92, 0.16, 0.22), "blocked": (0.20, 0.17, 0.27),
}

_NAMED: Dict[str, RGB] = {
    "red": (0.92, 0.16, 0.22), "green": (0.25, 0.85, 0.45),
    "blue": (0.25, 0.50, 0.98), "yellow": (1.00, 0.82, 0.22),
    "orange": (1.00, 0.55, 0.15), "gray": (0.50, 0.50, 0.58),
    "grey": (0.50, 0.50, 0.58), "purple": (0.65, 0.35, 0.95),
    "cyan": (0.30, 0.90, 0.95), "white": (0.95, 0.95, 0.95),
    "black": (0.14, 0.13, 0.18), "pink": (1.0, 0.50, 0.70),
    "brown": (0.55, 0.35, 0.20), "gold": (1.0, 0.78, 0.25),
    "maroon": (0.55, 0.12, 0.18), "violet": (0.60, 0.35, 0.95),
    "lime": (0.65, 0.95, 0.25), "crimson": (0.85, 0.12, 0.25),
    "darkred": (0.60, 0.10, 0.12), "magenta": (0.95, 0.30, 0.85),
}


def zone_color(name: str | None, fallback: RGB = (0.80, 0.80, 0.82)) -> RGB:
    """Map a free-form color word to an RGB accent color."""
    if name is None:
        return fallback
    key = name.lower()
    if key in _NAMED:
        return _NAMED[key]
    hue = (zlib.crc32(key.encode()) % 360) / 360.0
    return colorsys.hsv_to_rgb(hue, 0.75, 0.95)
