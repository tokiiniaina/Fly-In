"""Floating voxel island: quantized dunes, dirt strata on the flanks."""

from __future__ import annotations

import math
from typing import Callable, List, Tuple

from panda3d.core import NodePath

from . import palette as P
from .meshkit import RGB, MeshBuilder, mix, shade
from .terrain import _hash, value_noise

CELL = 2.0
STEP = 1.0
DEPTH = -9.0


def raw_height(x: float, y: float) -> float:
    """Unquantized dune height."""
    return (value_noise(x * 0.035, y * 0.04, 1) - 0.5) * 3.4 \
        + (value_noise(x * 0.09 + 5, y * 0.1, 2) - 0.5) * 1.2


class Island:
    """Builds the island mesh from a flattening mask."""

    def __init__(self, bounds: Tuple[float, float, float, float],
                 mask: Callable[[float, float], float],
                 route_dist: Callable[[float, float], float]) -> None:
        """``mask`` is 0 on flat ground; ``route_dist`` is the distance
        to the nearest track."""
        x0, y0, x1, y1 = bounds
        self.nx = int((x1 - x0) / CELL) + 1
        self.ny = int((y1 - y0) / CELL) + 1
        self.x0, self.y0 = x0, y0
        self.x1, self.y1 = x0 + self.nx * CELL, y0 + self.ny * CELL
        self._route = route_dist
        self.h: List[List[float]] = []
        for j in range(self.ny):
            row = []
            for i in range(self.nx):
                x, y = self._center(i, j)
                value = raw_height(x, y) * mask(x, y)
                row.append(math.floor(value / STEP) * STEP)
            self.h.append(row)

    def _center(self, i: int, j: int) -> Tuple[float, float]:
        return self.x0 + (i + 0.5) * CELL, self.y0 + (j + 0.5) * CELL

    def height(self, x: float, y: float) -> float:
        """Top height of the voxel column under (x, y)."""
        i = int((x - self.x0) / CELL)
        j = int((y - self.y0) / CELL)
        if 0 <= i < self.nx and 0 <= j < self.ny:
            return self.h[j][i]
        return DEPTH

    def corners(self) -> List[Tuple[float, float]]:
        """The four corners of the island."""
        return [(self.x0, self.y0), (self.x1, self.y0),
                (self.x1, self.y1), (self.x0, self.y1)]

    def _top_color(self, i: int, j: int, x: float, y: float) -> RGB:
        pick = _hash(i, j, 3)
        base = P.SAND_B if pick > 0.62 else P.SAND_C if pick < 0.2 \
            else P.SAND_A
        if value_noise(x * 0.07, y * 0.07, 9) > 0.7 and pick < 0.5:
            base = P.SAND_D
        base = shade(base, 0.95 + 0.1 * _hash(i, j, 4))
        if self._route(x, y) < 1.3:
            base = mix(base, P.SAND_D, 0.55)
        return base

    def _strata(self, z: float, jitter: float) -> RGB:
        index = min(len(P.STRATA) - 1, int((-z) / 1.8))
        return shade(P.STRATA[index], 0.94 + 0.1 * jitter)

    def build(self) -> NodePath:
        """Create the island mesh."""
        mb = MeshBuilder("island")
        for j in range(self.ny):
            for i in range(self.nx):
                self._cell(mb, i, j)
        mb.quad((self.x0, self.y0, DEPTH), (self.x1, self.y0, DEPTH),
                (self.x1, self.y1, DEPTH), (self.x0, self.y1, DEPTH),
                P.STRATA[-1], ((self.x0 + self.x1) / 2,
                               (self.y0 + self.y1) / 2, DEPTH + 1))
        return mb.build()

    def _cell(self, mb: MeshBuilder, i: int, j: int) -> None:
        h = self.h[j][i]
        xa, ya = self.x0 + i * CELL, self.y0 + j * CELL
        xb, yb = xa + CELL, ya + CELL
        cx, cy = (xa + xb) / 2, (ya + yb) / 2
        ref = (cx, cy, h - 0.6)
        mb.quad((xa, ya, h), (xb, ya, h), (xb, yb, h), (xa, yb, h),
                self._top_color(i, j, cx, cy), ref)
        sides = (
            (0, -1, (xa, ya, xb, ya)), (0, 1, (xa, yb, xb, yb)),
            (-1, 0, (xa, ya, xa, yb)), (1, 0, (xb, ya, xb, yb)),
        )
        for di, dj, (ax, ay, bx, by) in sides:
            ni, nj = i + di, j + dj
            outside = not (0 <= ni < self.nx and 0 <= nj < self.ny)
            low = DEPTH if outside else self.h[nj][ni]
            if low >= h:
                continue
            jitter = _hash(i, j, 7 + di * 3 + dj)
            if outside:
                z = h
                while z > low + 1e-6:
                    nz = max(low, math.floor((z - 1e-6) / 1.8) * 1.8)
                    mb.quad((ax, ay, z), (bx, by, z), (bx, by, nz),
                            (ax, ay, nz), self._strata(z, jitter), ref)
                    z = nz
            else:
                mb.quad((ax, ay, h), (bx, by, h), (bx, by, low),
                        (ax, ay, low), shade(P.SAND_D, 0.92 + 0.1 * jitter),
                        ref)
