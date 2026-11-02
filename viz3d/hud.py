"""Minimal dark interface for the Panda3D viewer."""

from __future__ import annotations

from typing import Any, Callable

from direct.gui.DirectGui import (
    DirectButton,
    DirectFrame,
    DirectScrolledFrame,
)
from direct.gui.OnscreenText import OnscreenText
from direct.gui import DirectGuiGlobals as DGG
from panda3d.core import TextNode

from . import palette as P
from .contract import Graph

PANEL = (0.035, 0.055, 0.12, 0.94)
BUTTON = (0.08, 0.10, 0.20, 1.0)
BUTTON_HOVER = (0.15, 0.12, 0.34, 1.0)
SELECTED = (0.27, 0.20, 0.72, 1.0)
INK = (0.84, 0.88, 0.98, 1.0)
MUTED = (0.52, 0.59, 0.75, 1.0)
ACCENT = (0.48, 0.38, 1.0, 1.0)


class Hud:
    """Create and update the viewer's flat, keyboard-friendly interface."""

    def __init__(
        self,
        app: Any,
        callbacks: dict[str, Callable[..., None]],
        map_entries: list[tuple[str, str]],
        current_map: str,
        graph: Graph,
    ) -> None:
        """Create controls, map selection and status information."""
        self.app = app
        self.root = app.aspect2d.attachNewNode("flyin_hud")
        parent = self.root
        self._map_buttons: dict[str, Any] = {}
        self._map_markers: dict[str, Any] = {}
        self._map_rows: dict[str, Any] = {}
        self._active_buttons: set[str] = set()
        self._legend_nodes: list[Any] = []
        self._map_names = {
            filename: display for filename, display in map_entries
        }
        self._map_callback = callbacks["map"]

        self._build_top_bar(parent, callbacks)
        self._build_map_panel(parent, map_entries, current_map)
        self._build_bottom_bar(parent, graph)
        self.set_current_map(current_map)
        self._resize(None)
        app.accept("window-event", self._resize)

    def _resize(self, window: Any) -> None:
        """Scale the fixed layout to fit the current window aspect ratio."""
        if window is None:
            window = self.app.win
        if window is None:
            return
        aspect = window.getXSize() / max(1, window.getYSize())
        self.root.setScale(min(1.0, aspect / 1.94))

    def _build_top_bar(
        self,
        parent: Any,
        callbacks: dict[str, Callable[..., None]],
    ) -> None:
        """Build the compact top bar and connect every playback button."""
        self.bar = DirectFrame(
            parent=parent,
            frameColor=PANEL,
            frameSize=(-1.88, 1.88, -0.075, 0.075),
            pos=(0, 0, 0.92),
        )
        self._text(self.bar, "FLY-IN", (-1.78, -0.018), 0.065,
                   INK, TextNode.ALeft)
        self.buttons: dict[str, Any] = {}
        x = -0.84
        for key, label, width in (
            ("play", "Play", 0.16),
            ("step", "Step", 0.15),
            ("restart", "Restart", 0.22),
        ):
            self._add_button(callbacks, key, label, width, x)
            x += width + 0.015
        self.speed_text = self._text(
            self.bar, "Speed x1", (-0.085, -0.012), 0.029, MUTED,
            TextNode.ACenter,
        )
        x = 0.02
        for key, label, width in (
            ("slower", "-", 0.075),
            ("faster", "+", 0.075),
            ("routes", "Routes", 0.20),
            ("labels", "Names", 0.20),
        ):
            self._add_button(callbacks, key, label, width, x)
            x += width + 0.015
        self.turn_text = self._text(
            self.bar, "TURN 0 / 0", (1.76, 0.012), 0.041, INK,
            TextNode.ARight,
        )
        self.count_text = self._text(
            self.bar, "0 delivered  |  0 remaining", (1.76, -0.04),
            0.025, MUTED, TextNode.ARight,
        )

    def _add_button(
        self,
        callbacks: dict[str, Callable[..., None]],
        key: str,
        label: str,
        width: float,
        x: float,
    ) -> None:
        """Create one flat playback button with hover feedback."""
        button = DirectButton(
            parent=self.bar,
            text=label,
            scale=0.038,
            frameSize=(-width / 0.038 / 2, width / 0.038 / 2,
                       -0.72, 0.72),
            frameColor=BUTTON,
            text_fg=INK,
            text_scale=0.9,
            relief=0,
            pos=(x + width / 2, 0, -0.006),
            command=callbacks[key],
            pressEffect=1,
        )
        button.bind(DGG.ENTER, self._hover_button, [key, True])
        button.bind(DGG.EXIT, self._hover_button, [key, False])
        self.buttons[key] = button

    def _build_map_panel(
        self,
        parent: Any,
        map_entries: list[tuple[str, str]],
        current_map: str,
    ) -> None:
        """Build a scrollable list containing only discovered map files."""
        self.map_panel = DirectFrame(
            parent=parent,
            frameColor=PANEL,
            frameSize=(-1.88, -1.16, -0.76, 0.82),
            pos=(0, 0, 0),
        )
        self._text(
            self.map_panel, "MAPS", (-1.78, 0.72), 0.044, INK,
            TextNode.ALeft,
        )
        self.map_scroll = DirectScrolledFrame(
            parent=self.map_panel,
            frameColor=(0, 0, 0, 0),
            frameSize=(-1.82, -1.21, -0.68, 0.67),
            canvasSize=(-0.30, 0.30, -max(0.70, len(map_entries) * 0.065),
                        0.0),
            scrollBarWidth=0.025,
            manageScrollBars=True,
            autoHideScrollBars=True,
            verticalScroll_frameColor=(0.10, 0.08, 0.22, 1.0),
        )
        canvas = self.map_scroll.getCanvas()
        for index, (filename, display) in enumerate(map_entries):
            z = -0.045 - index * 0.065
            row = DirectFrame(
                parent=canvas,
                frameColor=BUTTON,
                frameSize=(-0.28, 0.30, -0.025, 0.025),
                pos=(0, 0, z),
            )
            self._map_rows[filename] = row
            marker = DirectFrame(
                parent=canvas,
                frameColor=ACCENT,
                frameSize=(-0.30, -0.285, -0.025, 0.025),
                pos=(0, 0, z),
            )
            marker.hide()
            self._map_markers[filename] = marker
            button = DirectButton(
                parent=canvas,
                text=self._shorten(display, 25),
                scale=0.038,
                frameSize=(-7.35, 7.4, -0.80, 0.80),
                frameColor=(0, 0, 0, 0),
                text_fg=INK,
                text_align=TextNode.ALeft,
                text_pos=(-7.0, -0.015),
                relief=0,
                pos=(0, 0, z),
                command=self._map_callback,
                extraArgs=[filename],
                pressEffect=1,
            )
            button.bind(DGG.ENTER, self._hover_map, [filename, True])
            button.bind(DGG.EXIT, self._hover_map, [filename, False])
            self._map_buttons[filename] = button

    def _build_bottom_bar(self, parent: Any, graph: Graph) -> None:
        """Build a quiet status bar with the selected map and zone."""
        self.bottom = DirectFrame(
            parent=parent,
            frameColor=PANEL,
            frameSize=(-1.88, 1.88, -0.11, 0.11),
            pos=(0, 0, -0.87),
        )
        self.map_status = self._text(
            self.bottom, "", (-1.78, 0.055), 0.028, INK, TextNode.ALeft,
        )
        self.info_text = self._text(
            self.bottom, "Select a map or click a zone", (-0.48, 0.055),
            0.023, MUTED, TextNode.ALeft,
        )
        self.banner = self._text(
            self.bottom, "", (1.76, 0.055), 0.026, ACCENT, TextNode.ARight,
        )
        self._build_zone_legend(graph)

    def _build_zone_legend(self, graph: Graph) -> None:
        """Show only the zone kinds and colors present in the loaded map."""
        for node in self._legend_nodes:
            node.removeNode()
        self._legend_nodes.clear()
        order = ("start", "end", "normal", "priority", "restricted",
                 "blocked")
        entries: dict[str, list[tuple[str, tuple[float, ...]]]] = {}
        for zone in graph.zones.values():
            kind = ("start" if zone.is_start else "end" if zone.is_end
                    else zone.zone_type.value)
            color = P.zone_color(zone.color, P.PAD_DEFAULT[kind])
            name = zone.color or "default"
            entries.setdefault(kind, [])
            if not any(existing == name for existing, _ in entries[kind]):
                entries[kind].append((name, color))

        legend: list[tuple[str, tuple[float, ...]]] = []
        for kind in order:
            colors = entries.get(kind)
            if not colors:
                continue
            for name, color in colors:
                label = kind.upper()
                if len(colors) > 1:
                    label += f" ({name})"
                legend.append((label, color))

        self._legend_nodes.append(self._text(
            self.bottom, "ZONE TYPES", (-1.78, -0.065), 0.026, INK,
            TextNode.ALeft,
        ))
        available = 2.72
        label_scale = 0.027
        widths = [0.07 + len(label) * 0.014 for label, _ in legend]
        if sum(widths) > available:
            label_scale = max(0.018, label_scale * available / sum(widths))
            widths = [0.07 + len(label) * label_scale * 0.52
                      for label, _ in legend]
        total_width = sum(widths)
        x = -1.10 + max(0.0, (available - total_width) / 2)
        for index, (label, color) in enumerate(legend):
            self._legend_nodes.append(DirectFrame(
                parent=self.bottom,
                frameColor=(*color, 1.0),
                frameSize=(-0.018, 0.018, -0.018, 0.018),
                pos=(x, 0, -0.055),
            ))
            self._legend_nodes.append(self._text(
                self.bottom, label, (x + 0.03, -0.069), label_scale, INK,
                TextNode.ALeft,
            ))
            x += widths[index]

    def set_graph(self, graph: Graph) -> None:
        """Refresh the legend after another map has been loaded."""
        self._build_zone_legend(graph)

    @staticmethod
    def _shorten(text: str, limit: int) -> str:
        """Shorten a label so it stays inside its interface area."""
        return text if len(text) <= limit else text[:limit - 3] + "..."

    @staticmethod
    def _text(
        parent: Any,
        text: str,
        pos: tuple[float, float],
        scale: float,
        color: tuple[float, ...],
        align: Any,
    ) -> Any:
        """Create a readable text node with a consistent visual style."""
        return OnscreenText(
            text=text,
            parent=parent,
            pos=pos,
            scale=scale,
            fg=color,
            align=align,
            mayChange=True,
        )

    def set_current_map(self, filename: str) -> None:
        """Highlight the selected map and update the bottom status."""
        for name, button in self._map_buttons.items():
            selected = name == filename
            button["frameColor"] = (0, 0, 0, 0)
            self._map_rows[name]["frameColor"] = (
                SELECTED if selected else BUTTON
            )
            if selected:
                self._map_markers[name].show()
            else:
                self._map_markers[name].hide()
        self.map_status.setText(
            f"MAP  {self._map_names.get(filename, filename)}"
        )

    def set_button_state(self, key: str, active: bool) -> None:
        """Show whether a toggle or playback control is currently active."""
        if active:
            self._active_buttons.add(key)
        else:
            self._active_buttons.discard(key)
        if key in self.buttons:
            self.buttons[key]["frameColor"] = (
                SELECTED if active else BUTTON
            )

    def _hover_button(self, key: str, hovered: bool, event: Any) -> None:
        """Show a hover state without hiding a control's active state."""
        active = key in self._active_buttons
        self.buttons[key]["frameColor"] = (
            SELECTED if active else BUTTON_HOVER if hovered else BUTTON
        )

    def _hover_map(self, filename: str, hovered: bool, event: Any) -> None:
        """Highlight a map row on hover, preserving the selected row."""
        selected = self._map_markers[filename].isHidden() is False
        self._map_rows[filename]["frameColor"] = (
            SELECTED if selected else BUTTON_HOVER if hovered else BUTTON
        )

    def update(
        self,
        turn: int,
        total: int,
        delivered: int,
        drones: int,
        speed: float,
        playing: bool,
        selection: str,
        finished: bool,
        map_status: str,
    ) -> None:
        """Refresh counters, button labels and the current status line."""
        self.turn_text.setText(f"TURN {turn} / {total}")
        self.count_text.setText(
            f"{delivered} delivered  |  {drones - delivered} remaining"
        )
        self.speed_text.setText(f"Speed x{speed:.2g}")
        self.buttons["play"]["text"] = "Pause" if playing else "Play"
        self.set_button_state("play", playing)
        self.info_text.setText(self._shorten(selection, 55))
        self.map_status.setText(self._shorten(map_status, 30))
        self.banner.setText("COMPLETE" if finished else "")
