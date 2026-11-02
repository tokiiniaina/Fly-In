"""Startup menu for the Panda3D viewer."""

from __future__ import annotations

from typing import Any, Callable

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectButton, DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

BACKGROUND = (0.025, 0.04, 0.10, 0.94)
BUTTON = (0.09, 0.13, 0.25, 0.92)
BUTTON_HOVER = (0.16, 0.18, 0.34, 0.98)
PLAY_BUTTON = (0.25, 0.20, 0.68, 0.98)
INK = (0.91, 0.93, 1.0, 1.0)
MUTED = (0.48, 0.56, 0.74, 1.0)
ACCENT = (0.43, 0.32, 1.0, 1.0)


class StartMenu:
    """Display the title and connect the startup actions."""

    def __init__(
        self,
        app: Any,
        turns: int,
        drones: int,
        play: Callable[[], None],
        maps: Callable[[], None],
        quit_game: Callable[[], None],
    ) -> None:
        """Create a responsive menu over the existing map scene."""
        self.app = app
        self.root = app.aspect2d.attachNewNode("start_menu")
        self.panel = DirectFrame(
            parent=self.root,
            frameColor=BACKGROUND,
            frameSize=(-0.70, 0.70, -1.0, 1.0),
            pos=(-1.08, 0, 0),
        )
        self._text(
            "FLY-IN", (-1.55, 0.45), 0.115, INK, TextNode.ALeft,
        )
        DirectFrame(
            parent=self.root,
            frameColor=ACCENT,
            frameSize=(-0.075, 0.075, -0.008, 0.008),
            pos=(-1.53, 0, 0.345),
        )
        self._text(
            "Drones are interesting.", (-1.55, 0.29), 0.035, MUTED,
            TextNode.ALeft,
        )
        self._text(
            f"TURN 0 / {turns}    |    0 / {drones}", (1.76, 0.91),
            0.027, INK,
            TextNode.ARight,
        )
        self._buttons: list[Any] = []
        self._add_button("Play", -0.20, PLAY_BUTTON, play)
        self._add_button("Maps", -0.42, BUTTON, maps)
        self._add_button("Quit", -0.64, BUTTON, quit_game)
        self._text(
            "FLY-IN  -  DRONE ROUTING SIMULATION",
            (-1.55, -0.89), 0.018, MUTED, TextNode.ALeft,
        )
        self._resize(None)
        app.accept("window-event", self._resize)

    def _text(
        self,
        text: str,
        pos: tuple[float, float],
        scale: float,
        color: tuple[float, float, float, float],
        align: Any,
    ) -> Any:
        """Create one menu text item."""
        return OnscreenText(
            text=text,
            parent=self.root,
            pos=pos,
            scale=scale,
            fg=color,
            align=align,
            mayChange=True,
        )

    def _add_button(
        self,
        label: str,
        z: float,
        color: tuple[float, float, float, float],
        callback: Callable[[], None],
    ) -> None:
        """Create a large flat menu button with hover feedback."""
        x = -1.10
        frame = DirectFrame(
            parent=self.root,
            frameColor=color,
            frameSize=(-0.45, 0.45, -0.08, 0.08),
            pos=(x, 0, z),
        )
        button = DirectButton(
            parent=self.root,
            text=label,
            text_fg=INK,
            text_scale=0.04,
            text_align=TextNode.ALeft,
            text_pos=(-0.30, -0.014),
            scale=1,
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.45, 0.45, -0.08, 0.08),
            pos=(x, 0, z),
            relief=0,
            command=callback,
            pressEffect=1,
        )
        button.bind(DGG.ENTER, self._hover, [frame, True, color])
        button.bind(DGG.EXIT, self._hover, [frame, False, color])
        self._buttons.append(button)

    @staticmethod
    def _hover(button: Any, hovered: bool, base: Any, event: Any) -> None:
        """Highlight a button while the pointer is over it."""
        button["frameColor"] = BUTTON_HOVER if hovered else base

    def _resize(self, window: Any) -> None:
        """Keep the menu proportions stable when the window is resized."""
        if window is None:
            window = self.app.win
        if window is None:
            return
        aspect = window.getXSize() / max(1, window.getYSize())
        self.root.setScale(min(1.0, aspect / 1.6))

    def show(self) -> None:
        """Show the startup menu."""
        self.root.show()

    def hide(self) -> None:
        """Hide the startup menu."""
        self.root.hide()
