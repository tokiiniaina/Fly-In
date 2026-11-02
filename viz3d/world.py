"""Builds the floating voxel island from a parsed map."""

from __future__ import annotations

import math
import random
import zlib
from typing import Any, Dict, List, Tuple

from panda3d.core import NodePath, TextNode

from .contract import Graph, Zone, ZoneType
from .assets import load_model, site_model_path
from . import palette as P
from . import props
from .island import Island
from .meshkit import MeshBuilder
from .terrain import smoothstep

Seg = Tuple[float, float, float, float]
SITE_SCALE = P.UNIT


def slot_offsets(
    n: int, direction: Tuple[float, float] = (1.0, 0.0)
) -> List[Tuple[float, float]]:
    """Standing offsets for ``n`` drones, oriented across their route."""
    presets = {1: [(0.0, 0.0)], 2: [(-2.0, 0.0), (2.0, 0.0)],
               3: [(-2.0, -1.2), (2.0, -1.2), (0.0, 1.9)],
               4: [(-2.0, -1.9), (2.0, -1.9), (-2.0, 1.9), (2.0, 1.9)]}
    if n in presets:
        local = presets[n]
    else:
        local = [(0.0, 0.0)]
        ring = 1
        while len(local) < n:
            count = 6 * ring
            for k in range(count):
                a = 2 * math.pi * k / count + 0.4
                local.append((math.cos(a) * 4.0 * ring,
                              math.sin(a) * 4.0 * ring))
            ring += 1

    length = math.hypot(*direction)
    if length <= 1e-9:
        direction = (1.0, 0.0)
        length = 1.0
    ux, uy = direction[0] / length, direction[1] / length
    return [
        (-x * uy + y * ux, x * ux + y * uy)
        for x, y in local
    ]


class World:
    """The physical scene generated from the input graph."""

    def __init__(self, parent: NodePath, graph: Graph,
                 loader: Any = None, seed: int = 7) -> None:
        """Create island, sites, trails, cacti and labels."""
        self.graph = graph
        self.loader = loader
        self.root = parent.attachNewNode("world")
        self.rng = random.Random(seed)
        self.scale = self._compute_scale()
        self.pos: Dict[str, Tuple[float, float]] = {
            z.name: (z.x * self.scale, z.y * self.scale)
            for z in graph.zones.values()
        }
        self.pad_h: Dict[str, float] = {
            z.name: props.PAD_HEIGHT * P.UNIT for z in graph.zones.values()
        }
        self.routes: Dict[str, Seg] = {}
        self._layout_routes()
        self.sites: Dict[str, NodePath] = {}
        self.label_nodes: Dict[str, NodePath] = {}
        self._build_island()
        self._build_sites()
        self._build_trails()
        self._build_scatter()

    # ---------------------------------------------------------- geometry
    @staticmethod
    def _kind(zone: Zone) -> str:
        if zone.is_start:
            return "start"
        if zone.is_end:
            return "end"
        return zone.zone_type.value

    def _compute_scale(self) -> float:
        zones = list(self.graph.zones.values())
        best = 1e9
        for i, a in enumerate(zones):
            for b in zones[i + 1:]:
                best = min(best, math.hypot(a.x - b.x, a.y - b.y))
        if best >= 1e8 or best <= 0:
            return 8.0
        return min(16.0, max(5.0, 24.0 / best))

    def _radius(self, name: str) -> float:
        return props.PAD_RADIUS[self._kind(self.graph.zones[name])] * P.UNIT

    def _layout_routes(self) -> None:
        for conn in self.graph.connections:
            ax, ay = self.pos[conn.a]
            bx, by = self.pos[conn.b]
            length = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / length, (by - ay) / length
            ra, rb = self._radius(conn.a) + 0.6, self._radius(conn.b) + 0.6
            self.routes[conn.name] = (ax + ux * ra, ay + uy * ra,
                                      bx - ux * rb, by - uy * rb)

    def standing_point(self, zone: str, slot: int = 0, count: int = 1,
                       direction: Tuple[float, float] = (1.0, 0.0)
                       ) -> Tuple[float, float, float]:
        """World position under a drone standing on a zone's pad."""
        x, y = self.pos[zone]
        dx, dy = slot_offsets(max(count, slot + 1), direction)[slot]
        return (x + dx * P.UNIT, y - 0.4 + dy * P.UNIT, self.pad_h[zone])

    def route_point(self, conn_name: str, a: str,
                    t: float) -> Tuple[float, float, float]:
        """Point along a route measured from zone ``a`` (t in 0..1)."""
        conn = next(c for c in self.graph.connections
                    if c.name == conn_name)
        x0, y0, x1, y1 = self.routes[conn_name]
        if a != conn.a:
            x0, y0, x1, y1 = x1, y1, x0, y0
        return (x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                props.PAD_HEIGHT * P.UNIT)

    def bounds(self) -> Tuple[float, float, float, float]:
        """Bounding rectangle of all sites."""
        xs = [p[0] for p in self.pos.values()]
        ys = [p[1] for p in self.pos.values()]
        return min(xs), min(ys), max(xs), max(ys)

    def island_corners(self) -> List[Tuple[float, float]]:
        """Corners of the floating island."""
        return self.island.corners()

    # ------------------------------------------------------------ island
    @staticmethod
    def _seg_distance(x: float, y: float, seg: Seg) -> float:
        x0, y0, x1, y1 = seg
        vx, vy = x1 - x0, y1 - y0
        ln = vx * vx + vy * vy
        t = 0.0 if ln == 0 else max(0.0, min(1.0, (
            (x - x0) * vx + (y - y0) * vy) / ln))
        return math.hypot(x - (x0 + vx * t), y - (y0 + vy * t))

    def _route_dist(self, x: float, y: float) -> float:
        best = 1e9
        for seg in self.routes.values():
            best = min(best, self._seg_distance(x, y, seg))
        return best

    def _mask(self, x: float, y: float) -> float:
        site = 1.0
        for name, (sx, sy) in self.pos.items():
            kind = self._kind(self.graph.zones[name])
            flat = (14.0 if kind in ("start", "end") else 10.0) * P.UNIT
            d = math.hypot(x - sx, y - (sy + 3.5 * P.UNIT))
            site = min(site, smoothstep(flat, flat + 7.0, d))
        return min(site, smoothstep(2.4, 5.0, self._route_dist(x, y)))

    def _build_island(self) -> None:
        x0, y0, x1, y1 = self.bounds()
        self.island = Island((x0 - 16, y0 - 16, x1 + 16, y1 + 28),
                             self._mask, self._route_dist)
        self.island.build().reparentTo(self.root)

    # ------------------------------------------------------------- sites
    def _build_sites(self) -> None:
        for index, zone in enumerate(self.graph.zones.values()):
            kind = self._kind(zone)
            accent = P.zone_color(zone.color, P.PAD_DEFAULT[kind])
            rng = random.Random(zlib.crc32(zone.name.encode()))
            asset = site_model_path(kind, zone.color)
            if self.loader is not None and asset.is_file():
                node = load_model(self.loader, asset)
            else:
                node = props.build_site(kind, accent, rng, index)
            node.reparentTo(self.root)
            x, y = self.pos[zone.name]
            node.setPos(x, y, 0)
            node.setScale(P.UNIT)
            self.sites[zone.name] = node
            self._label(zone, x, y)

    def _label(self, zone: Zone, x: float, y: float) -> None:
        text = TextNode("label_" + zone.name)
        text.setText(zone.name)
        text.setAlign(TextNode.ACenter)
        text.setTextColor(1, 0.95, 0.85, 1)
        text.setShadow(0.06, 0.06)
        text.setShadowColor(0.15, 0.05, 0.2, 1)
        node = self.root.attachNewNode(text)
        node.setPos(x, y - 1.0, self.pad_h[zone.name] + 7.5 * P.UNIT)
        node.setScale(1.6)
        node.setBillboardPointEye()
        node.setLightOff(1)
        node.setShaderOff(1)
        node.setFogOff()
        node.setDepthWrite(False)
        node.setDepthTest(False)
        node.setBin("fixed", 40)
        self.label_nodes[zone.name] = node

    # ------------------------------------------------------------ trails
    def _build_trails(self) -> None:
        mb = MeshBuilder("trails")
        for conn in self.graph.connections:
            x0, y0, x1, y1 = self.routes[conn.name]
            length = math.hypot(x1 - x0, y1 - y0)
            if length < 1.0:
                continue
            ux, uy = (x1 - x0) / length, (y1 - y0) / length
            nx, ny = -uy, ux
            danger = any(self.graph.zones[n].zone_type is ZoneType.RESTRICTED
                         for n in (conn.a, conn.b))
            color = (1.0, 0.5, 0.25) if danger else P.CYAN
            rows = min(conn.max_link_capacity, 4)
            steps = max(2, int(length / 1.3))
            for r in range(rows):
                off = (r - (rows - 1) / 2) * 1.0
                for k in range(steps):
                    t = (k + 0.5) / steps
                    px = x0 + (x1 - x0) * t + nx * off
                    py = y0 + (y1 - y0) * t + ny * off
                    size = 0.7 if k % 2 else 0.5
                    mb.box((size, size, 0.2), color, (px, py, 0.14),
                           glow=True)
        mb.build().reparentTo(self.root)

    # ----------------------------------------------------------- scatter
    def _build_scatter(self) -> None:
        mb = MeshBuilder("scatter")
        isl = self.island
        area = (isl.x1 - isl.x0) * (isl.y1 - isl.y0)
        for _ in range(int(min(260, area / 60))):
            x = self.rng.uniform(isl.x0 + 3, isl.x1 - 3)
            y = self.rng.uniform(isl.y0 + 3, isl.y1 - 3)
            if self._mask(x, y) < 0.97:
                continue
            z = isl.height(x, y)
            if self.rng.random() < 0.7:
                props.cactus(mb, x, y, z, self.rng)
            else:
                props.rock(mb, x, y, z, self.rng)
        pyramid_position = self._clear_pyramid_position(24.0)
        if pyramid_position is not None:
            x, y = pyramid_position
            props.pyramid(mb, x, y, isl.height(x, y), 24.0)
        mb.build().reparentTo(self.root)

    def _clear_pyramid_position(
        self, base: float,
    ) -> Tuple[float, float] | None:
        """Find a clear background spot or omit the pyramid on dense maps."""
        margin = base / 2 + 5.0
        x0, y0 = self.island.x0 + margin, self.island.y0 + margin
        x1, y1 = self.island.x1 - margin, self.island.y1 - margin
        if x0 >= x1 or y0 >= y1:
            return None

        zone_clearance = margin + max(props.PAD_RADIUS.values()) * P.UNIT
        route_clearance = margin
        for y in range(int(y0), int(y1) + 1, 8):
            for x in range(int(x0), int(x1) + 1, 8):
                if any(
                    math.hypot(x - zx, y - zy) < zone_clearance
                    for zx, zy in self.pos.values()
                ):
                    continue
                if self._route_dist(x, y) < route_clearance:
                    continue
                if self._mask(x, y) < 0.97:
                    continue
                return float(x), float(y)
        return None
