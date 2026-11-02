"""The Panda3D application that replays the simulation engine's turns."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    ClockObject, LineSegs, NodePath, Point2, Point3, TextNode, Vec4,
    loadPrcFileData,
)

from .camera import CameraRig
from .choreo import Choreography, Phase, Step
from .contract import Graph, TurnResult
from .hud import Hud
from .lighting import HAZE, setup_lighting
from .map_selection import MapSelection
from .assets import MESAS_MODEL, SKY_MODEL, load_model
from . import palette as P
from .meshkit import MeshBuilder
from .robot import RobotModel
from .start_menu import StartMenu
from .world import SITE_SCALE, World
from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function import MapParser
from viz3d.adapter import build_scene_data

Vec3t = Tuple[float, float, float]
SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
TRAIL_N = 9
DECOR_OFFSET = 10.0
MAP_ORDER = (
    "01_linear_path.txt",
    "02_simple_fork.txt",
    "03_basic_capacity.txt",
    "01_dead_end_trap.txt",
    "02_circular_loop.txt",
    "03_priority_puzzle.txt",
    "01_maze_nightmare.txt",
    "02_capacity_hell.txt",
    "03_ultimate_challenge.txt",
    "01_the_impossible_dream.txt",
)


def angle_diff(a: float, b: float) -> float:
    """Shortest signed difference between two headings in degrees."""
    return (b - a + 180.0) % 360.0 - 180.0


def sample_path(points: List[Vec3t], fraction: float
                ) -> Tuple[Vec3t, Tuple[float, float], float, float]:
    """Position, direction, travelled and total length along a polyline."""
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    total = sum(lengths)
    target = fraction * total
    walked = 0.0
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if length > 1e-6 and (walked + length >= target - 1e-9):
            k = min(1.0, max(0.0, (target - walked) / length))
            pos = (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k,
                   a[2] + (b[2] - a[2]) * k)
            return pos, ((b[0] - a[0]) / length, (b[1] - a[1]) / length), \
                target, total
        walked += length
    return points[-1], (0.0, 0.0), total, total


class DroneActor:
    """A robot plus its floating id tag and animation memory."""

    def __init__(self, parent: NodePath, drone_id: int,
                 proto: NodePath, loader: Any) -> None:
        """Create the drone, its tag and its thruster trail."""
        self.drone_id = drone_id
        self.model = RobotModel(parent, f"drone{drone_id}", loader)
        self.heading = 180.0
        self.cheer = 0.0
        tag = TextNode(f"tag{drone_id}")
        tag.setText(f"D{drone_id}")
        tag.setAlign(TextNode.ACenter)
        tag.setTextColor(1.0, 0.93, 0.8, 1)
        tag.setShadow(0.07, 0.07)
        tag.setShadowColor(0.08, 0.06, 0.05, 1)
        self.tag = self.model.root.attachNewNode(tag)
        self.tag.setPos(0, 0, 4.5)
        self.tag.setScale(0.5)
        self.tag.setBillboardPointEye()
        self.tag.setLightOff(1)
        self.tag.setShaderOff(1)
        self.tag.setFogOff()
        self.tag.setDepthTest(False)
        self.tag.setDepthWrite(False)
        self.tag.setBin("fixed", 50)
        self.trail = [proto.copyTo(parent) for _ in range(TRAIL_N)]
        for node in self.trail:
            node.hide()

    def hide_trail(self) -> None:
        """Hide the thruster trail."""
        for node in self.trail:
            node.hide()


class FlyInApp(ShowBase):  # type: ignore[misc,unused-ignore]
    """Real-time viewer driven by the engine's turn list."""

    def __init__(self, graph: Graph, turns: List[TurnResult],
                 map_name: str = "map", offscreen: bool = False,
                 size: Tuple[int, int] = (1600, 900),
                 autoplay: bool = False,
                 map_directory: Optional[Path] = None,
                 map_file: Optional[str] = None) -> None:
        """Build the scene, the HUD and the playback state."""
        loadPrcFileData("", f"window-title FlyIn - {map_name}\n"
                        f"win-size {size[0]} {size[1]}\n"
                        "audio-library-name null\n"
                        "framebuffer-multisample 1\nmultisamples 2\n"
                        + ("window-type offscreen\n" if offscreen else ""))
        super().__init__()
        self.map_directory = (
            map_directory
            or Path(__file__).resolve().parents[1] / "maps"
        )
        self.map_file = map_file or map_name
        self.map_status = ""
        self.setBackgroundColor(Vec4(*HAZE, 1))
        x0, y0, x1, y1 = self._map_bounds(graph)
        extent = max(x1 - x0, y1 - y0) + 70.0
        self.sun = setup_lighting(self.render, ((x0 + x1) / 2,
                                                (y0 + y1) / 2, 0), extent,
                                  2048)
        self.camLens.setFov(40)
        self.camLens.setNearFar(2, 4000)
        self.rig = CameraRig(self, self.sun, extent)
        self.rig.heading = 45.0
        self.rig.pitch = 32.0
        self.sky = load_model(self.loader, SKY_MODEL)
        self.sky.reparentTo(self.render)
        self.index = 0
        self.progress = 0.0
        self.speed_i = 2
        self.playing = autoplay
        self.simulation_started = False
        self.routes_on = False
        self.pause_at: Optional[int] = None
        self.selected: Optional[str] = None
        self.anim_clock = 0.0
        self.names_on = True
        self._build_map_scene(graph, turns)
        self.hud = Hud(self, {
            "play": self.toggle_play, "step": self.step_turn,
            "restart": self.restart_playback,
            "slower": lambda: self._speed(-1),
            "faster": lambda: self._speed(1),
            "routes": self.toggle_routes, "labels": self.toggle_names,
            "map": self.load_map,
        }, self._map_entries(), self.map_file, graph)
        self.hud.root.hide()
        self.hud.set_button_state("labels", self.names_on)
        self.start_menu = StartMenu(
            self,
            len(self.turns),
            graph.nb_drones,
            self._start_from_menu,
            self._open_map_selection,
            self.userExit,
        )
        self.map_selection = MapSelection(
            self,
            self._map_entries(),
            self._select_map_from_menu,
            self._return_to_start_menu,
        )
        for key, fn in (("n", self.step_turn),
                        ("r", self.restart_playback),
                        ("v", self.toggle_routes),
                        ("l", self.toggle_names),
                        ("]", lambda: self._speed(1)),
                        ("[", lambda: self._speed(-1)),
                        ("escape", self._handle_escape)):
            self.accept(key, fn)
        self.window_size = (self.win.getXSize(), self.win.getYSize())
        self.accept("window-event", self._window_resized)
        self.accept("mouse1-up", self._click)
        self.accept("space", self._handle_space)
        self._apply(0.0)
        self.taskMgr.add(self._tick, "tick")

    def _start_from_menu(self) -> None:
        """Close the startup menu and start the selected simulation."""
        self.start_menu.hide()
        self.scene_root.show()
        self.background_root.show()
        self.sky.show()
        self.hud.root.show()
        self.toggle_play()

    def _open_map_selection(self) -> None:
        """Show only the map list and hide the 3D scene."""
        self.start_menu.hide()
        self.hud.root.hide()
        self.scene_root.hide()
        self.background_root.hide()
        self.sky.hide()
        self.map_selection.show()

    def _return_to_start_menu(self) -> None:
        """Return from map selection to the startup menu."""
        self.map_selection.hide()
        self.scene_root.show()
        self.background_root.show()
        self.sky.show()
        self.start_menu.show()

    def _select_map_from_menu(self, filename: str) -> None:
        """Load a chosen map, then start playback in the 3D view."""
        self.load_map(filename)
        if self.map_status.startswith("LOAD ERROR"):
            return
        self.map_selection.hide()
        self.scene_root.show()
        self.background_root.show()
        self.sky.show()
        self.hud.root.show()
        self.toggle_play()

    def _handle_space(self) -> None:
        """Start from the menu, or toggle playback after leaving it."""
        if not self.map_selection.root.isHidden():
            return
        if not self.start_menu.root.isHidden():
            self._start_from_menu()
        else:
            self.toggle_play()

    def _handle_escape(self) -> None:
        """Return to the startup menu from map selection, otherwise quit."""
        if not self.map_selection.root.isHidden():
            self._return_to_start_menu()
            return
        self.userExit()

    def _window_resized(self, window: Any) -> None:
        """Refit the selected map when the application window changes size."""
        if window != self.win or self.win is None:
            return
        size = (self.win.getXSize(), self.win.getYSize())
        if size == self.window_size:
            return
        self.window_size = size
        self.rig.fit(
            self.world.island_corners(), horizontal_offset=0.25
        )

    @staticmethod
    def _map_bounds(graph: Graph) -> Tuple[float, float, float, float]:
        """Return map coordinate bounds before the 3D world is built."""
        xs = [zone.x for zone in graph.zones.values()]
        ys = [zone.y for zone in graph.zones.values()]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _display_map_name(filename: str) -> str:
        """Convert a map filename into a short readable menu label."""
        stem = Path(filename).stem
        parts = stem.split("_", 1)
        label = parts[1] if len(parts) == 2 and parts[0].isdigit() else stem
        return label.replace("_", " ").title()

    def _map_entries(self) -> list[tuple[str, str]]:
        """List available maps in the subject's increasing challenge order."""
        order = {filename: index for index, filename in enumerate(MAP_ORDER)}
        paths = sorted(
            self.map_directory.glob("*.txt"),
            key=lambda path: (order.get(path.name, len(order)), path.name),
        )
        return [
            (path.name, self._display_map_name(path.name))
            for path in paths
        ]

    def _build_map_scene(self, graph: Graph, turns: List[TurnResult]) -> None:
        """Build only the 3D objects that belong to the selected map."""
        old_scene = getattr(self, "scene_root", None)
        if old_scene is not None and not old_scene.isEmpty():
            old_scene.removeNode()
        self.scene_root = self.render.attachNewNode("map_scene")
        self.graph = graph
        self.turns = turns
        self.choreo = Choreography(graph, turns)
        self.world = World(self.scene_root, graph, self.loader)
        x0, y0, x1, y1 = self.world.bounds()
        self.rig.extent = max(x1 - x0, y1 - y0) + 70.0
        self.rig.fit(
            self.world.island_corners(), horizontal_offset=0.25
        )
        old_background = getattr(self, "background_root", None)
        if old_background is not None and not old_background.isEmpty():
            old_background.removeNode()
        self.background_root = self.render.attachNewNode("map_background")
        mesas = load_model(self.loader, MESAS_MODEL)
        mesas.setPos((x0 + x1) / 2, y1 + DECOR_OFFSET, 0)
        mesas.reparentTo(self.background_root)
        proto_mb = MeshBuilder("trail")
        proto_mb.box((0.5, 0.5, 0.5), P.CYAN, glow=True)
        proto = proto_mb.build()
        self.actors = {
            drone: DroneActor(self.scene_root, drone, proto, self.loader)
            for drone in range(1, graph.nb_drones + 1)
        }
        if not self.names_on:
            for actor in self.actors.values():
                actor.tag.hide()
        self._build_overlay()
        self._build_selection_ring()
        if not self.names_on:
            for label in self.world.label_nodes.values():
                label.hide()
        self.durations = [self._duration(i) for i in range(len(turns))]
        self.selected = None
        self.index = 0
        self.progress = 0.0
        self.pause_at = None
        self.simulation_started = False
        self.playing = False
        self.map_status = f"MAP  {self._display_map_name(self.map_file)}"

    # --------------------------------------------------------- controls
    @property
    def finished(self) -> bool:
        """Whether every turn has been played."""
        return self.index >= len(self.turns)

    def toggle_play(self) -> None:
        """Play or pause (restarts when finished)."""
        if self.finished:
            self.restart_playback()
        self.simulation_started = True
        self.playing = not self.playing
        self.pause_at = None

    def step_turn(self) -> None:
        """Play exactly one turn then pause."""
        if self.finished:
            return
        self.simulation_started = True
        self.pause_at = self.index + 1
        self.playing = True

    def restart_playback(self) -> None:
        """Go back to turn 0 (paused)."""
        self.index, self.progress = 0, 0.0
        self.playing, self.pause_at = False, None
        self.simulation_started = False
        for actor in self.actors.values():
            actor.cheer = 0.0
        self._apply(0.0)

    def _speed(self, delta: int) -> None:
        self.speed_i = min(len(SPEEDS) - 1, max(0, self.speed_i + delta))

    def load_map(self, filename: str) -> None:
        """Parse and display a selected map without changing the engine."""
        path = self.map_directory / filename
        try:
            data = MapParser().parse(str(path))
            lines = Simulator(data).run()
            graph, turns = build_scene_data(data, lines)
        except (OSError, ValueError) as error:
            self.map_status = f"LOAD ERROR  {self._short_status(str(error))}"
            return
        self.map_file = path.name
        self._build_map_scene(graph, turns)
        self.hud.set_graph(graph)
        self.hud.set_current_map(self.map_file)
        self._apply(0.0)

    @staticmethod
    def _short_status(message: str) -> str:
        """Keep a loading error readable in the bottom status bar."""
        return message if len(message) <= 68 else message[:65] + "..."

    def toggle_routes(self) -> None:
        """Show or hide the connection overlay."""
        self.routes_on = not self.routes_on
        if self.routes_on:
            self.overlay.show()
        else:
            self.overlay.hide()
        self.hud.set_button_state("routes", self.routes_on)

    def toggle_names(self) -> None:
        """Show or hide zone names and drone tags."""
        self.names_on = not self.names_on
        for node in self.world.label_nodes.values():
            node.show() if self.names_on else node.hide()
        for actor in self.actors.values():
            actor.tag.show() if self.names_on else actor.tag.hide()
        self.hud.set_button_state("labels", self.names_on)

    def seek(self, index: int, progress: float = 0.0) -> None:
        """Jump to a state (used by the screenshot mode)."""
        self.index = max(0, min(index, len(self.turns)))
        self.progress = progress
        self._apply(0.0)

    # ----------------------------------------------------------- scene
    def _build_overlay(self) -> None:
        segs = LineSegs("overlay")
        segs.setThickness(4)
        self.overlay = self.scene_root.attachNewNode("overlay_root")
        for conn in self.graph.connections:
            x0, y0, x1, y1 = self.world.routes[conn.name]
            cap = conn.max_link_capacity
            color = {1: (0.4, 0.95, 1.0), 2: (0.7, 1.0, 0.4)}.get(
                cap, (1.0, 0.82, 0.3))
            segs.setColor(*color, 1)
            segs.moveTo(x0, y0, 0.8)
            segs.drawTo(x1, y1, 0.8)
            text = TextNode("cap_" + conn.name)
            text.setText(f"cap {cap}")
            text.setAlign(TextNode.ACenter)
            text.setTextColor(*color, 1)
            text.setShadow(0.06, 0.06)
            node = self.overlay.attachNewNode(text)
            node.setPos((x0 + x1) / 2, (y0 + y1) / 2, 1.6)
            node.setScale(1.1)
            node.setBillboardPointEye()
            node.setLightOff(1)
            node.setShaderOff(1)
            node.setFogOff()
            node.setDepthTest(False)
        line = self.overlay.attachNewNode(segs.create())
        line.setLightOff(1)
        line.setShaderOff(1)
        line.setFogOff()
        line.setDepthTest(False)
        line.setBin("fixed", 30)
        self.overlay.hide()
        if self.routes_on:
            self.overlay.show()

    def _build_selection_ring(self) -> None:
        mb = MeshBuilder("select")
        count = 32
        for i in range(count):
            a = 2 * math.pi * i / count
            mb.box((0.9, 0.22, 0.08), (1.0, 0.85, 0.5),
                   (math.cos(a), math.sin(a), 0.1),
                   (math.degrees(a) + 90, 0, 0), glow=True)
        self.ring = mb.build()
        self.ring.reparentTo(self.scene_root)
        self.ring.hide()

    def _duration(self, index: int) -> float:
        longest = 0.0
        for step in self.choreo.steps[index].values():
            if step.phase is not Phase.IDLE:
                _, _, _, total = sample_path(self._points(step), 1.0)
                longest = max(longest, total)
        return min(4.5, max(1.5, longest / 16.0))

    def _stand(self, zone: str, slot: int,
               direction: Tuple[float, float] = (1.0, 0.0)) -> Vec3t:
        return self.world.standing_point(
            zone, slot, self.choreo.layout[zone], direction
        )

    def _route_direction(self, src: str, dst: str) -> Tuple[float, float]:
        """Return the map direction from one zone to another."""
        a = self.world.pos[src]
        b = self.world.pos[dst]
        return b[0] - a[0], b[1] - a[1]

    def _points(self, step: Step) -> List[Vec3t]:
        """The polyline a drone follows during one step."""
        direction = self._route_direction(step.src, step.dst)
        stand_src = self._stand(step.src, step.src_slot, direction)
        stand_dst = self._stand(step.dst, step.dst_slot, direction)
        if step.connection is None:
            return [stand_src, stand_src]
        w = self.world
        start = w.route_point(step.connection, step.src, 0.0)
        mid = w.route_point(step.connection, step.src, 0.5)
        end = w.route_point(step.connection, step.src, 1.0)
        arc = 3.0 * P.UNIT
        mid = (mid[0], mid[1], mid[2] + arc)
        if step.phase is Phase.ENTER:
            return [stand_src, start, mid]
        if step.phase is Phase.EXIT:
            return [mid, end, stand_dst]
        return [stand_src, start, end, stand_dst]

    # --------------------------------------------------------- playback
    def _tick(self, task: Any) -> Any:
        dt = min(0.1, ClockObject.getGlobalClock().getDt())
        self.rig.update(dt)
        self.sky.setPos(self.camera.getPos(self.render))
        label = min(3.2, 1.0 + self.rig.dist * 0.014)
        for node in self.world.label_nodes.values():
            node.setScale(label)
        tag = min(0.7, 0.25 + self.rig.dist * 0.003)
        for actor in self.actors.values():
            actor.tag.setScale(tag)
        sim_dt = 0.0
        if self.playing and not self.finished:
            sim_dt = dt
            speed = SPEEDS[self.speed_i]
            self.progress += dt * speed / self.durations[self.index]
            while self.progress >= 1.0 and not self.finished:
                self.progress -= 1.0
                self.index += 1
                if self.pause_at is not None and self.index >= self.pause_at:
                    self.playing, self.pause_at = False, None
                    self.progress = 0.0
                    break
            if self.finished:
                self.progress, self.playing = 0.0, False
        self._apply(sim_dt)
        return task.cont

    def _apply(self, dt: float) -> None:
        self.anim_clock += dt
        visible = (
            self.simulation_started or self.index > 0 or self.progress > 0
        )
        for actor in self.actors.values():
            if visible:
                actor.model.root.show()
            else:
                actor.model.root.hide()
        if self.finished:
            self._pose_final(dt)
        else:
            steps = self.choreo.steps[self.index]
            for drone, actor in self.actors.items():
                self._pose(actor, steps[drone], self.progress, dt)
        self._update_hud()
        self._update_ring()

    def _face(self, actor: DroneActor, target: float, dt: float) -> None:
        actor.heading += angle_diff(actor.heading, target) * min(1.0, dt * 9)
        actor.model.root.setH(actor.heading)

    def _pose(self, actor: DroneActor, step: Step, p: float,
              dt: float) -> None:
        model = actor.model
        t = self.anim_clock + actor.drone_id * 0.7
        idle_heading = self.rig.heading + 180.0
        if step.phase is Phase.IDLE:
            if step.src == self.graph.start.name:
                next_zone = self.graph.neighbors(step.src)[0].other(step.src)
                direction = self._route_direction(step.src, next_zone)
            else:
                direction = (1.0, 0.0)
            x, y, z = self._stand(step.src, step.src_slot, direction)
            model.root.setPos(x, y, z)
            if step.src == self.graph.end.name:
                actor.cheer = max(0.0, actor.cheer - dt * 0.6)
            self._face(actor, idle_heading, dt)
            model.pose(0.0, 0.0, t, actor.cheer)
            model.root.clearColorScale()
            actor.hide_trail()
            return
        f = p
        points = self._points(step)
        pos, (dx, dy), travelled, total = sample_path(points, f)
        model.root.setPos(*pos)
        if abs(dx) + abs(dy) > 1e-6 and 0.0 < f < 1.0:
            self._face(actor, math.degrees(math.atan2(-dx, dy)), dt)
        ramp = min(1.0, p * 7.0) * min(1.0, (1.0 - p) * 7.0)
        if step.phase is Phase.ARRIVE and p > 0.8:
            actor.cheer = min(1.0, actor.cheer + dt * 3.0)
            self._face(actor, idle_heading, dt)
        else:
            actor.cheer = 0.0 if step.phase is not Phase.ARRIVE \
                else actor.cheer
        model.pose(travelled / 6.0 * 2 * math.pi, ramp, t, actor.cheer)
        self._trail(actor, points, travelled, total, ramp)
        if step.phase in (Phase.ENTER, Phase.EXIT):
            model.root.setColorScale(1.0, 0.78, 0.66, 1)
        else:
            model.root.clearColorScale()

    def _trail(self, actor: DroneActor, points: List[Vec3t],
               travelled: float, total: float, strength: float) -> None:
        """Place the thruster trail on the path behind the drone."""
        for k, node in enumerate(actor.trail):
            behind = travelled - 2.0 - k * 1.6
            if behind < 0 or strength < 0.15 or total <= 0:
                node.hide()
                continue
            p, _, _, _ = sample_path(points, behind / total)
            node.setPos(p[0], p[1], p[2] + actor.model.hover * P.UNIT)
            node.setScale(max(0.1, (1.0 - k / TRAIL_N) * strength) * P.UNIT)
            node.show()

    def _pose_final(self, dt: float) -> None:
        last = self.choreo.steps[-1] if self.choreo.steps else {}
        for drone, actor in self.actors.items():
            step = last.get(drone)
            zone = step.dst if step else self.graph.start.name
            slot = step.dst_slot if step else drone - 1
            direction = (
                self._route_direction(step.src, step.dst)
                if step and step.src != step.dst else (1.0, 0.0)
            )
            x, y, z = self._stand(zone, slot, direction)
            actor.model.root.setPos(x, y, z)
            actor.cheer = max(0.0, actor.cheer - dt * 0.6)
            self._face(actor, self.rig.heading + 180.0, dt)
            actor.model.pose(0.0, 0.0, self.anim_clock + drone * 0.7,
                             actor.cheer)
            actor.model.root.clearColorScale()
            actor.hide_trail()

    # -------------------------------------------------------------- hud
    def _positions_after(self, index: int) -> Dict[int, Optional[str]]:
        """Zone of every drone at the end of ``index`` completed turns."""
        if index == 0:
            return {d: self.graph.start.name
                    for d in range(1, self.graph.nb_drones + 1)}
        snaps = self.turns[index - 1].snapshots
        return {d: s.zone for d, s in snaps.items()}

    def _log_lines(self) -> List[str]:
        shown = self.index + (0 if self.finished or
                              (self.progress == 0 and not self.playing)
                              else 1)
        lines: List[str] = []
        for number in range(max(1, shown - 13), shown + 1):
            if number > len(self.turns):
                break
            parts = []
            for m in self.turns[number - 1].movements:
                if m.in_transit:
                    parts.append(f"D{m.drone_id}~>{m.dst}")
                else:
                    parts.append(f"D{m.drone_id}>{m.dst}")
            lines.append(f"T{number}: " + " ".join(parts))
        return lines

    def _zone_info(self, name: str) -> str:
        zone = self.graph.zones[name]
        kind = "start" if zone.is_start else "end" if zone.is_end \
            else zone.zone_type.value
        cap = "unlimited" if zone.capacity is None else str(zone.capacity)
        here = sorted(d for d, z in self._positions_after(self.index).items()
                      if z == name)
        links = ", ".join(
            f"{c.other(name)} (cap {c.max_link_capacity})"
            for c in self.graph.neighbors(name)) or "none"
        drones = ", ".join(f"D{d}" for d in here[:12]) or "none"
        if len(here) > 12:
            drones += f" +{len(here) - 12}"
        return (f"{name}\ntype: {kind}\ncoords: ({zone.x}, {zone.y})\n"
                f"capacity: {cap}\ncolor: {zone.color or 'none'}\n"
                f"drones here: {drones}\nlinks: {links}")

    def _update_hud(self) -> None:
        total = len(self.turns)
        shown = min(total, self.index + (1 if self.progress > 0 or
                                         (self.playing and not
                                          self.finished) else 0))
        delivered = self.turns[self.index - 1].delivered \
            if self.index > 0 else 0
        selection = self._zone_status(self.selected) if self.selected \
            else "Select a map or click a zone"
        self.hud.update(shown, total, delivered, self.graph.nb_drones,
                        SPEEDS[self.speed_i], self.playing, selection,
                        self.finished, self.map_status)

    def _zone_status(self, name: str) -> str:
        """Return a short status line for the selected zone."""
        zone = self.graph.zones[name]
        kind = "start" if zone.is_start else "end" if zone.is_end \
            else zone.zone_type.value
        count = sum(
            1 for position in self._positions_after(self.index).values()
            if position == name
        )
        return f"{name}  |  {kind}  |  {count} drone(s)"

    def _update_ring(self) -> None:
        if self.selected is None:
            self.ring.hide()
            return
        x, y = self.world.pos[self.selected]
        zone = self.graph.zones[self.selected]
        kind = "start" if zone.is_start else "end" if zone.is_end \
            else zone.zone_type.value
        from .props import PAD_RADIUS
        radius = (PAD_RADIUS[kind] + 0.9) * SITE_SCALE
        pulse = 1.0 + 0.02 * math.sin(self.anim_clock * 3.0 + 1.0)
        self.ring.setPos(x, y, 0.1)
        self.ring.setScale(radius * pulse, radius * pulse, 1.0)
        self.ring.show()

    def _click(self) -> None:
        watcher = getattr(self, "mouseWatcherNode", None)
        if watcher is None or not watcher.hasMouse():
            return
        mouse = watcher.getMouse()
        aspect = self.win.getXSize() / max(1, self.win.getYSize())
        hud_scale = self.hud.root.getScale()[0]
        if (mouse.x * aspect < -1.16 * hud_scale
                or mouse.y > 0.84 * hud_scale
                or mouse.y < -0.83 * hud_scale):
            return
        best: Optional[str] = None
        best_d = 0.11
        probe = Point2()
        for name, (x, y) in self.world.pos.items():
            z = self.world.pad_h[name] + 1.5
            cam_p = self.camera.getRelativePoint(self.render, Point3(x, y, z))
            if cam_p.y <= 0 or not self.camLens.project(cam_p, probe):
                continue
            d = math.hypot(probe.x - mouse.x, (probe.y - mouse.y) * 0.6)
            if d < best_d:
                best, best_d = name, d
        self.selected = best
