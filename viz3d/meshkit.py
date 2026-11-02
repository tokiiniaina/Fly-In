"""Tiny procedural mesh toolkit: beveled boxes, cylinders, flat shading.

Every primitive is written with flat normals (low-poly look) and per-vertex
albedo colors. Parts that should glow are routed to a separate unlit
batch so they stay bright regardless of the sun.
"""

from __future__ import annotations

import math
from typing import Any, List, Sequence, Tuple

from panda3d.core import (
    ColorAttrib, Geom, GeomNode, GeomTriangles, GeomVertexData,
    GeomVertexFormat, GeomVertexWriter, Mat4, NodePath, Point3,
    TransformState, Vec3,
)

RGB = Tuple[float, float, float]
Vec = Tuple[float, float, float]


def mix(a: RGB, b: RGB, t: float) -> RGB:
    """Linear blend between two colors."""
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t,
            a[2] + (b[2] - a[2]) * t)


def shade(c: RGB, k: float) -> RGB:
    """Multiply a color by a brightness factor."""
    return (min(1.0, c[0] * k), min(1.0, c[1] * k), min(1.0, c[2] * k))


class _Batch:
    """Flat lists of vertex attributes."""

    def __init__(self) -> None:
        """Start empty."""
        self.pos: List[Vec] = []
        self.nrm: List[Vec] = []
        self.col: List[RGB] = []


class MeshBuilder:
    """Accumulates primitives and turns them into a NodePath."""

    def __init__(self, name: str) -> None:
        """Create an empty builder."""
        self.name = name
        self._solid = _Batch()
        self._glow = _Batch()

    # ------------------------------------------------------------ basics
    @staticmethod
    def _matrix(pos: Vec, hpr: Vec) -> Mat4:
        return TransformState.makePosHpr(
            Point3(*pos), Vec3(*hpr)).getMat()

    def tri(self, a: Vec, b: Vec, c: Vec, color: RGB, ref: Vec,
            glow: bool = False) -> None:
        """Add one triangle whose normal points away from ``ref``."""
        va, vb, vc = Vec3(*a), Vec3(*b), Vec3(*c)
        n = (vb - va).cross(vc - va)
        if n.length() < 1e-9:
            return
        n.normalize()
        centroid = (va + vb + vc) / 3.0
        if n.dot(centroid - Vec3(*ref)) < 0:
            vb, vc = vc, vb
            n = -n
        batch = self._glow if glow else self._solid
        for v in (va, vb, vc):
            batch.pos.append((v.x, v.y, v.z))
            batch.nrm.append((n.x, n.y, n.z))
            batch.col.append(color)

    def quad(self, a: Vec, b: Vec, c: Vec, d: Vec, color: RGB, ref: Vec,
             glow: bool = False) -> None:
        """Add a quad as two triangles."""
        self.tri(a, b, c, color, ref, glow)
        self.tri(a, c, d, color, ref, glow)

    # -------------------------------------------------------- primitives
    def box(self, size: Vec, color: RGB, pos: Vec = (0, 0, 0),
            hpr: Vec = (0, 0, 0), bevel: float = 0.0, glow: bool = False,
            top: RGB | None = None) -> None:
        """Add a (beveled) box centered on ``pos``."""
        m = self._matrix(pos, hpr)
        h = [size[0] / 2, size[1] / 2, size[2] / 2]
        b = min(bevel, h[0] * 0.9, h[1] * 0.9, h[2] * 0.9)
        ref = self._xf(m, (0, 0, 0))

        def corner(axis: int, s: Sequence[int]) -> Vec:
            p = [s[i] * (h[i] - b) for i in range(3)]
            p[axis] = s[axis] * h[axis]
            return self._xf(m, (p[0], p[1], p[2]))

        for axis in range(3):
            u, v = [i for i in range(3) if i != axis]
            for sa in (-1, 1):
                pts = []
                for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                    s = [0, 0, 0]
                    s[axis], s[u], s[v] = sa, su, sv
                    pts.append(corner(axis, s))
                col = top if (top is not None and axis == 2 and sa == 1) \
                    else color
                self.quad(pts[0], pts[1], pts[2], pts[3], col, ref, glow)
        if b <= 0:
            return
        edge_col = shade(color, 1.06)
        for a1 in range(3):
            for a2 in range(a1 + 1, 3):
                t = 3 - a1 - a2
                for s1 in (-1, 1):
                    for s2 in (-1, 1):
                        def pt(axis: int, st: int) -> Vec:
                            s = [0, 0, 0]
                            s[a1], s[a2], s[t] = s1, s2, st
                            return corner(axis, s)
                        self.quad(pt(a1, -1), pt(a1, 1), pt(a2, 1),
                                  pt(a2, -1), edge_col, ref, glow)
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    sg = (sx, sy, sz)
                    self.tri(corner(0, sg), corner(1, sg), corner(2, sg),
                             edge_col, ref, glow)

    def cyl(self, radius: float, height: float, color: RGB,
            pos: Vec = (0, 0, 0), hpr: Vec = (0, 0, 0), segs: int = 14,
            radius_top: float | None = None, glow: bool = False,
            caps: bool = True, top: RGB | None = None) -> None:
        """Add a (possibly tapered) cylinder whose axis is local Z."""
        m = self._matrix(pos, hpr)
        rt = radius if radius_top is None else radius_top
        hz = height / 2
        ref = self._xf(m, (0, 0, 0))
        ring_b: List[Vec] = []
        ring_t: List[Vec] = []
        for i in range(segs):
            ang = 2 * math.pi * i / segs
            ca, sa = math.cos(ang), math.sin(ang)
            ring_b.append(self._xf(m, (radius * ca, radius * sa, -hz)))
            ring_t.append(self._xf(m, (rt * ca, rt * sa, hz)))
        cb = self._xf(m, (0, 0, -hz))
        ct = self._xf(m, (0, 0, hz))
        for i in range(segs):
            j = (i + 1) % segs
            self.quad(ring_b[i], ring_b[j], ring_t[j], ring_t[i],
                      color, ref, glow)
            if caps:
                self.tri(cb, ring_b[j], ring_b[i], color, ref, glow)
                if rt > 1e-6:
                    self.tri(ct, ring_t[i], ring_t[j],
                             top or color, ref, glow)

    @staticmethod
    def _xf(m: Mat4, p: Vec) -> Vec:
        q = m.xformPoint(Point3(*p))
        return (q.x, q.y, q.z)

    # ------------------------------------------------------------- build
    @staticmethod
    def _geom(batch: _Batch, name: str) -> Any:
        vdata = GeomVertexData(name, GeomVertexFormat.getV3n3c4(),
                               Geom.UHStatic)
        vdata.setNumRows(len(batch.pos))
        wv = GeomVertexWriter(vdata, "vertex")
        wn = GeomVertexWriter(vdata, "normal")
        wc = GeomVertexWriter(vdata, "color")
        for p, n, c in zip(batch.pos, batch.nrm, batch.col):
            wv.addData3(*p)
            wn.addData3(*n)
            wc.addData4(c[0], c[1], c[2], 1.0)
        prim = GeomTriangles(Geom.UHStatic)
        for i in range(0, len(batch.pos), 3):
            prim.addVertices(i, i + 1, i + 2)
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        return geom

    def build(self) -> NodePath:
        """Create the NodePath (a solid child and an unlit glow child)."""
        root = NodePath(self.name)
        if self._solid.pos:
            node = GeomNode(self.name + "_solid")
            node.addGeom(self._geom(self._solid, self.name))
            root.attachNewNode(node)
        if self._glow.pos:
            node = GeomNode(self.name + "_glow")
            node.addGeom(self._geom(self._glow, self.name + "g"))
            glow = root.attachNewNode(node)
            glow.setLightOff(1)
            glow.setShaderOff(1)
            glow.setTextureOff(1)
            glow.setFogOff()
            glow.setAttrib(ColorAttrib.makeVertex())
        return root
