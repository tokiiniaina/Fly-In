"""Voxel sites: towers, pads, the black cube, cacti, pyramid."""

from __future__ import annotations

import math
import random

from panda3d.core import NodePath

from . import palette as P
from .meshkit import RGB, MeshBuilder, shade

UNIT = P.UNIT
PAD_HEIGHT = 0.78
PAD_RADIUS = {"start": 5.0, "end": 5.0, "normal": 3.9, "priority": 4.1,
              "restricted": 4.0, "blocked": 3.6}
HALF = {"start": 4.6, "end": 4.6, "normal": 3.4, "priority": 3.6,
        "restricted": 3.5}


def pad(mb: MeshBuilder, half: float, color: RGB, accent: RGB) -> None:
    """A square landing pad with glowing edges."""
    mb.box((2 * half + 0.8, 2 * half + 0.8, 0.5), P.DARK2, (0, 0, 0.25))
    mb.box((2 * half, 2 * half, 0.2), color, (0, 0, 0.6))
    mb.box((2 * half - 2.4, 2 * half - 2.4, 0.1), P.DARK, (0, 0, 0.72))
    for s in (-1, 1):
        mb.box((2 * half, 0.2, 0.06), accent, (0, s * (half - 0.2), 0.72),
               glow=True)
        mb.box((0.2, 2 * half, 0.06), accent, (s * (half - 0.2), 0, 0.72),
               glow=True)
    for sx in (-1, 1):
        for sy in (-1, 1):
            mb.box((0.5, 0.5, 0.16), accent, (sx * (half - 0.2),
                   sy * (half - 0.2), 0.8), glow=True)


def tower(mb: MeshBuilder, x: float, y: float, layers: int,
          accent: RGB) -> None:
    """A white stepped tower with a flame on top."""
    z = PAD_HEIGHT - 0.1
    size, height = 3.8, 3.0
    for k in range(layers):
        mb.box((size, size, height), P.WHITE, (x, y, z + height / 2),
               top=shade(P.WHITE, 0.92))
        for s in (-1, 1):
            mb.box((0.7, 0.12, 0.9), P.DARK, (x + s * size * 0.2,
                   y - size / 2 - 0.02, z + height * 0.55))
            mb.box((0.12, 0.7, 0.9), P.DARK, (x + size / 2 + 0.02,
                   y + s * size * 0.2, z + height * 0.55))
        z += height
        mb.box((size + 0.2, size + 0.2, 0.22), accent, (x, y, z + 0.11),
               glow=True)
        z += 0.22
        size, height = size - 0.7, height - 0.3
    mb.box((size + 0.4, size + 0.4, 0.4), P.DARK2, (x, y, z + 0.2))
    mb.box((0.55, 0.55, 0.9), P.EMBER, (x, y, z + 0.85), glow=True)
    mb.box((0.3, 0.3, 0.6), P.YELLOW, (x, y, z + 1.45), glow=True)


def pole(mb: MeshBuilder, x: float, y: float, h: float, light: RGB) -> None:
    """A thin antenna pole with a glowing tip."""
    mb.box((0.28, 0.28, h), P.GREY_DK, (x, y, PAD_HEIGHT + h / 2))
    mb.box((0.9, 0.18, 0.18), P.GREY_DK, (x, y, PAD_HEIGHT + h * 0.7))
    mb.box((0.5, 0.5, 0.5), light, (x, y, PAD_HEIGHT + h + 0.2), glow=True)


def cactus(mb: MeshBuilder, x: float, y: float, z: float,
           rng: random.Random) -> None:
    """A voxel cactus."""
    u = UNIT
    h = rng.choice((1.2, 1.6, 2.0)) * u
    mb.box((0.5 * u, 0.5 * u, h), P.CACTUS, (x, y, z + h / 2))
    if h > 1.3 * u:
        side = rng.choice((-1, 1))
        mb.box((0.7 * u, 0.36 * u, 0.36 * u), P.CACTUS,
               (x + side * 0.5 * u, y, z + h * 0.55))
        mb.box((0.36 * u, 0.36 * u, 0.7 * u), P.CACTUS,
               (x + side * 0.74 * u, y, z + h * 0.55 + 0.3 * u))


def rock(mb: MeshBuilder, x: float, y: float, z: float,
         rng: random.Random) -> None:
    """A small blocky rock."""
    s = rng.uniform(0.5, 1.3) * UNIT
    mb.box((s, s * rng.uniform(0.7, 1.2), s * 0.7), P.SAND_D,
           (x, y, z + s * 0.3), (rng.uniform(0, 90), 0, 0))


def pyramid(mb: MeshBuilder, x: float, y: float, z: float,
            base: float) -> None:
    """A stepped sand pyramid."""
    size, k = base, 0
    while size > 1.6:
        col = P.SAND_D if k % 2 else shade(P.SAND_D, 0.86)
        mb.box((size, size, 1.2 * UNIT), col,
               (x, y, z + 0.6 * UNIT + k * 1.2 * UNIT))
        size -= 2.4 * UNIT
        k += 1


def build_site(kind: str, accent: RGB, rng: random.Random,
               variant: int) -> NodePath:
    """Return the NodePath of a complete site centered on its pad."""
    mb = MeshBuilder("site_" + kind)
    base = P.PAD_DEFAULT[kind]
    if kind == "blocked":
        _blocked(mb, rng)
    else:
        pad(mb, HALF[kind], accent if accent != (0.8, 0.8, 0.82) else base,
            accent)
        if kind == "start":
            tower(mb, 0, 8.4, 3, accent)
            mb.box((2.4, 1.6, 1.4), P.ORANGE_DK, (-5.2, 5.0, 1.4))
        elif kind == "end":
            tower(mb, 0, 8.4, 4, accent)
            pole(mb, 5.4, 6.0, 6.0, P.CYAN)
        elif kind == "priority":
            pole(mb, 3.0, 3.6, 7.0, P.GREEN)
            mb.box((1.8, 1.2, 0.12), P.GREY_DK, (-3.2, 4.4, 2.0),
                   (0, 20, 0))
            mb.box((0.14, 0.14, 1.6), P.GREY_DK, (-3.2, 4.4, 1.2))
        elif kind == "restricted":
            pole(mb, 3.2, 3.8, 6.0, P.EMBER)
            for k in range(8):
                col = P.EMBER if k % 2 else P.DARK
                mb.box((0.9, 0.5, 0.1), col, (-3.4 + k * 0.97, -3.7, 0.74))
        else:
            pole(mb, 2.6, 3.0, 4.6, P.CYAN)
            mb.box((1.0, 1.0, 1.0), P.ORANGE_DK, (-3.2, 4.6, 1.3),
                   (rng.uniform(0, 40), 0, 0))
    return mb.build()


def _blocked(mb: MeshBuilder, rng: random.Random) -> None:
    mb.box((4.6, 4.6, 3.8), P.DARK, (0, 0, 1.9))
    mb.box((4.8, 4.8, 0.4), P.DARK2, (0, 0, 3.7))
    for k in (-1, 1):
        mb.box((0.4, 0.1, 5.0), P.RED, (0, -2.33, 2.0), (0, 0, 45 * k),
               glow=True)
        mb.box((0.1, 0.4, 5.0), P.RED, (2.33, 0, 2.0), (90, 0, 45 * k),
               glow=True)
        mb.box((0.4, 0.1, 5.0), P.RED, (0, 2.33, 2.0), (0, 0, 45 * k),
               glow=True)
        mb.box((0.1, 0.4, 5.0), P.RED, (-2.33, 0, 2.0), (90, 0, 45 * k),
               glow=True)
    for sx in (-1, 1):
        mb.box((0.34, 0.1, 0.34), P.EMBER, (sx * 0.9, -2.34, 0.6),
               glow=True)
    for _ in range(5):
        a = rng.uniform(0, 2 * math.pi)
        mb.box((0.8, 0.8, 0.6), P.DARK2, (math.cos(a) * 3.8,
               math.sin(a) * 3.8, 0.3), (rng.uniform(0, 90), 0, 0))
