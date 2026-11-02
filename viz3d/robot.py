"""Hovering drone modeled after the orange concept sketch."""

from __future__ import annotations

import math
from typing import Any
from typing import Tuple

from panda3d.core import NodePath

from . import palette as P
from .assets import DRONE_MODEL, load_model
from .meshkit import MeshBuilder

Pos = Tuple[float, float, float]


def _attach(parent: NodePath, mb: MeshBuilder, pos: Pos = (0, 0, 0)
            ) -> NodePath:
    node = mb.build()
    node.reparentTo(parent)
    node.setPos(*pos)
    return node


class RobotModel:
    """An orange flying drone with a hull, cockpit and thrusters."""

    SCALE = 0.8

    def __init__(
        self,
        parent: NodePath,
        name: str = "drone",
        loader: Any = None,
        use_asset: bool = True,
    ) -> None:
        """Build the hierarchy under ``parent``."""
        self.root = parent.attachNewNode(name)
        self.root.setScale(P.UNIT)
        self.lift = self.root.attachNewNode("lift")
        self.rig = self.lift.attachNewNode("rig")
        self.rig.setScale(self.SCALE)
        self.hover = 2.35
        if use_asset and loader is not None:
            load_model(loader, DRONE_MODEL).reparentTo(self.rig)
        else:
            self._build_hull()

    def _build_hull(self) -> None:
        mb = MeshBuilder("hull")
        mb.box((2.3, 2.1, 0.95), P.ORANGE, bevel=0.28,
               top=(1.0, 0.70, 0.18))
        mb.box((1.9, 1.6, 0.1), P.ORANGE_DK, (0, -0.05, 0.5), bevel=0.04)
        mb.cyl(0.64, 0.26, P.GREY_DK, (0, -0.1, 0.66), segs=14,
               radius_top=0.42, top=(0.42, 0.44, 0.52))
        mb.cyl(0.26, 0.05, P.GREY_LT, (0, -0.1, 0.82), segs=10)
        # cockpit with the little blue pilot
        mb.box((1.2, 0.16, 0.92), P.GREY_DK, (0, 1.02, 0.02), bevel=0.07)
        mb.box((0.94, 0.1, 0.68), P.GLASS, (0, 1.1, 0.02), bevel=0.02)
        mb.box((0.34, 0.05, 0.42), P.BLUE, (0, 1.16, -0.02), glow=True)
        mb.box((0.18, 0.05, 0.18), (0.7, 0.9, 1.0), (0, 1.17, 0.17),
               glow=True)
        mb.box((0.14, 0.05, 0.1), P.GREEN, (0.27, 1.17, -0.12), glow=True)
        for sx in (-1, 1):
            for sz in (-1, 1):
                mb.box((0.14, 0.18, 0.14), P.GREY_DK,
                       (sx * 0.6, 1.08, sz * 0.46))
        # teal diamond badge on the left flank
        mb.box((0.06, 0.5, 0.5), P.TEAL, (-1.17, 0.45, 0.08),
               (0, 45, 0))
        mb.box((0.07, 0.24, 0.24), P.WHITE, (-1.18, 0.45, 0.08),
               (0, 45, 0))
        # belly plate and front shoulder blocks
        mb.box((1.8, 1.5, 0.3), P.GREY_DK, (0, 0, -0.56), bevel=0.08)
        for sx in (-1, 1):
            mb.box((0.64, 0.62, 0.62), P.ORANGE, (sx * 0.95, 0.72, -0.42),
                   bevel=0.13)
            mb.cyl(0.15, 0.06, P.GREY_DK, (sx * 0.95, 1.06, -0.42),
                   (0, 90, 0), segs=10)
            # side thruster pods
            mb.box((0.5, 0.6, 0.34), P.ORANGE_DK, (sx * 1.02, -0.1, 0.1))
            mb.cyl(0.4, 1.0, P.ORANGE, (sx * 1.42, -0.1, 0.1), (0, 90, 0),
                   segs=12)
            mb.cyl(0.3, 0.1, P.GREY_DK, (sx * 1.42, 0.45, 0.1),
                   (0, 90, 0), segs=10)
            mb.cyl(0.3, 0.08, P.CYAN, (sx * 1.42, -0.62, 0.1), (0, 90, 0),
                   segs=10, glow=True)
        # main rear thruster
        mb.box((0.9, 0.3, 0.5), P.GREY_DK, (0, -1.05, 0.0), bevel=0.05)
        mb.cyl(0.25, 0.06, P.CYAN, (0, -1.22, 0.0), (0, 90, 0), segs=10,
               glow=True)
        _attach(self.rig, mb)

    def pose(self, phase: float, flight: float, t: float,
             cheer: float = 0.0) -> None:
        """Pose the drone.

        ``flight`` in [0, 1] controls the flying attitude, ``t`` is the
        idle clock and ``cheer`` is the arrival spin.
        """
        bob = math.sin(t * 2.2) * 0.08
        self.hover = 2.8 + 0.25 * flight + 0.8 * cheer + bob
        self.lift.setZ(self.hover)
        self.lift.setP(-5.0 * flight)
        self.lift.setR(math.sin(t * 1.3) * 1.5
                       + math.sin(t * 9.0) * 12.0 * cheer)
