"""Orbit / pan / zoom camera that also keeps the shadows sharp."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, Tuple

from panda3d.core import NodePath, Point2, Point3, Vec3


class CameraRig:
    """Mouse and keyboard controlled orbit camera.

    Right mouse drag rotates, middle drag (or Shift + left drag) pans,
    the wheel zooms, WASD / arrows pan, Q/E rotate, +/- zoom.
    """

    def __init__(self, app: Any, sun: NodePath, extent: float) -> None:
        """Bind the rig to the application and to the sun light node."""
        self.app = app
        self.sun = sun
        self.extent = extent
        self.target = Vec3(0, 0, 0)
        self.heading = 0.0
        self.pitch = 50.0
        self.dist = 100.0
        self.sun_dir = Vec3(0.62, -0.30, 0.62)
        self.sun_dir.normalize()
        self._keys: Dict[str, bool] = {}
        self._drag: str | None = None
        self._last = Point2(0, 0)
        self.moved_while_dragging = False
        app.disableMouse()
        for key in ("w", "a", "s", "d", "q", "e", "arrow_up", "arrow_down",
                    "arrow_left", "arrow_right", "+", "-", "=", "shift"):
            app.accept(key, self._set, [key, True])
            app.accept(key + "-up", self._set, [key, False])
        app.accept("mouse3", self._begin, ["rotate"])
        app.accept("mouse3-up", self._end)
        app.accept("mouse2", self._begin, ["pan"])
        app.accept("mouse2-up", self._end)
        app.accept("wheel_up", self.zoom, [0.88])
        app.accept("wheel_down", self.zoom, [1.14])

    # ------------------------------------------------------------ input
    def _set(self, key: str, down: bool) -> None:
        self._keys[key] = down

    def _begin(self, mode: str) -> None:
        watcher = self.app.mouseWatcherNode
        if watcher.hasMouse():
            self._drag = mode
            self._last = Point2(watcher.getMouse())
            self.moved_while_dragging = False

    def _end(self) -> None:
        self._drag = None

    def zoom(self, factor: float) -> None:
        """Multiply the camera distance."""
        self.dist = min(self.extent * 2.5, max(14.0, self.dist * factor))

    def pan(self, right: float, forward: float) -> None:
        """Move the target on the ground relative to the heading."""
        h = math.radians(self.heading)
        self.target.x += math.cos(h) * right - math.sin(h) * forward
        self.target.y += math.sin(h) * right + math.cos(h) * forward

    # ----------------------------------------------------------- update
    def update(self, dt: float) -> None:
        """Apply input and place the camera and the sun."""
        watcher = self.app.mouseWatcherNode
        if self._drag and watcher.hasMouse():
            now = Point2(watcher.getMouse())
            dx, dy = now.x - self._last.x, now.y - self._last.y
            self._last = now
            if abs(dx) + abs(dy) > 0.002:
                self.moved_while_dragging = True
            if self._drag == "rotate":
                self.heading -= dx * 160.0
                self.pitch = min(82.0, max(14.0, self.pitch + dy * 90.0))
            else:
                k = self.dist * 0.9
                self.pan(-dx * k, -dy * k * 1.3)
        keys = self._keys
        speed = self.dist * 0.9 * dt
        self.pan(
            (keys.get("d", False) or keys.get("arrow_right", False)) * speed
            - (keys.get("a", False) or keys.get("arrow_left", False)) * speed,
            (keys.get("w", False) or keys.get("arrow_up", False)) * speed
            - (keys.get("s", False) or keys.get("arrow_down", False)) * speed)
        self.heading += (keys.get("q", False) - keys.get("e", False)) * 70 * dt
        if keys.get("+", False) or keys.get("=", False):
            self.zoom(1.0 - 1.2 * dt)
        if keys.get("-", False):
            self.zoom(1.0 + 1.2 * dt)
        self.place()

    def place(self) -> None:
        cam = self.app.camera
        cam.setPos(self.target)
        cam.setHpr(self.heading, -self.pitch, 0)
        cam.setPos(cam, 0, -self.dist, 0)
        film = min(self.extent * 2.0, max(70.0, self.dist * 1.7))
        reach = 420.0
        self.sun.setPos(self.target.x + self.sun_dir.x * reach,
                        self.target.y + self.sun_dir.y * reach,
                        self.target.z + self.sun_dir.z * reach)
        self.sun.lookAt(self.target.x, self.target.y, self.target.z)
        lens = self.sun.node().getLens()
        lens.setFilmSize(film, film)
        lens.setNearFar(reach - film * 1.3, reach + film * 1.3)

    # -------------------------------------------------------------- fit
    def _screen_bounds(self, pts: "list[Tuple[float, float]]"
                       ) -> Tuple[float, float, float, float]:
        """Screen-space bounds of all points (and their buildings)."""
        fov = self.app.camLens.getFov()
        tx = math.tan(math.radians(fov[0] / 2))
        ty = math.tan(math.radians(fov[1] / 2))
        xs: "list[float]" = []
        ys: "list[float]" = []
        for x, y in pts:
            for dy in (-6.0, 16.0):
                cam_p = self.app.camera.getRelativePoint(
                    self.app.render, Point3(x, y + dy, 0))
                if cam_p.y <= 0.1:
                    return -9.0, 9.0, -9.0, 9.0
                xs.append(cam_p.x / (cam_p.y * tx))
                ys.append(cam_p.z / (cam_p.y * ty))
        return min(xs), max(xs), min(ys), max(ys)

    def fit(
        self,
        points: Iterable[Tuple[float, float]],
        horizontal_offset: float = -0.14,
    ) -> None:
        """Frame points and place their center in the free screen area."""
        pts = list(points)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.target = Vec3((min(xs) + max(xs)) / 2,
                           (min(ys) + max(ys)) / 2 + 4.0, 0)
        hfov = math.radians(self.app.camLens.getFov()[0] / 2)
        for dist in range(40, int(self.extent * 3), 3):
            self.dist = float(dist)
            self.place()
            lo, hi, bot, top = self._screen_bounds(pts)
            if hi - lo <= 1.5 and top - bot <= 1.5:
                break
        for _ in range(3):
            self.place()
            lo, hi, bot, top = self._screen_bounds(pts)
            center = (lo + hi) / 2
            shift = (center - horizontal_offset) * self.dist * math.tan(hfov)
            self.pan(shift, 0.0)
        self.place()
