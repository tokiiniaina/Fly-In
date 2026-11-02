"""Full-screen map selection menu without the 3D map behind it."""

from __future__ import annotations

from typing import Any, Callable

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import (
    DirectButton,
    DirectFrame,
    DirectScrolledFrame,
)
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode

BACKGROUND = (0.025, 0.04, 0.10, 0.98)
ROW = (0.08, 0.11, 0.21, 1.0)
HOVER = (0.16, 0.13, 0.34, 1.0)
INK = (0.91, 0.93, 1.0, 1.0)
MUTED = (0.48, 0.56, 0.74, 1.0)


class MapSelection:
    """Show only available map names and load the selected map."""

    def __init__(
        self,
        app: Any,
        entries: list[tuple[str, str]],
        select: Callable[[str], None],
        back: Callable[[], None],
    ) -> None:
        """Create a scrollable list of maps and a back button."""
        self.root = app.aspect2d.attachNewNode("map_selection")
        DirectFrame(
            parent=self.root,
            frameColor=BACKGROUND,
            frameSize=(-2.0, 2.0, -1.0, 1.0),
        )
        self._text(
            self.root, "MAPS", (-0.88, 0.82), 0.075, INK, TextNode.ALeft,
        )
        self._text(
            self.root, "Choose a map to start its simulation",
            (-0.88, 0.70), 0.032, MUTED, TextNode.ALeft,
        )
        row_step = 0.115
        canvas_height = max(0.82, len(entries) * row_step + 0.04)
        self.list = DirectScrolledFrame(
            parent=self.root,
            frameColor=(0, 0, 0, 0),
            frameSize=(-0.88, 0.88, -0.65, 0.62),
            canvasSize=(-0.82, 0.82, -canvas_height, 0.0),
            scrollBarWidth=0.035,
            manageScrollBars=True,
            autoHideScrollBars=True,
            verticalScroll_frameColor=(0.10, 0.08, 0.22, 1.0),
        )
        canvas = self.list.getCanvas()
        self.buttons: dict[str, Any] = {}
        for index, (filename, label) in enumerate(entries):
            z = -0.055 - index * row_step
            row = DirectFrame(
                parent=canvas,
                frameColor=ROW,
                frameSize=(-0.80, 0.80, -0.045, 0.045),
                pos=(0, 0, z),
            )
            button = DirectButton(
                parent=canvas,
                text=label,
                text_fg=INK,
                text_scale=0.038,
                text_align=TextNode.ALeft,
                text_pos=(-0.74, -0.014),
                frameColor=(0, 0, 0, 0),
                frameSize=(-0.80, 0.80, -0.045, 0.045),
                pos=(0, 0, z),
                relief=0,
                command=select,
                extraArgs=[filename],
                pressEffect=1,
            )
            button.bind(DGG.ENTER, self._hover, [row, True])
            button.bind(DGG.EXIT, self._hover, [row, False])
            self.buttons[filename] = button
        self.back_button = DirectButton(
            parent=self.root,
            text="Back",
            text_fg=INK,
            text_scale=0.034,
            frameColor=ROW,
            frameSize=(-0.14, 0.14, -0.045, 0.045),
            pos=(-0.74, 0, -0.82),
            relief=0,
            command=back,
            pressEffect=1,
        )
        self.back_button.bind(DGG.ENTER, self._hover_button, [True])
        self.back_button.bind(DGG.EXIT, self._hover_button, [False])
        self._resize(None, app)
        app.accept("window-event", self._resize, [app])
        self.root.hide()

    @staticmethod
    def _text(
        parent: Any,
        text: str,
        pos: tuple[float, float],
        scale: float,
        color: tuple[float, float, float, float],
        align: Any,
    ) -> Any:
        """Create one line of menu text."""
        return OnscreenText(
            text=text,
            parent=parent,
            pos=pos,
            scale=scale,
            fg=color,
            align=align,
            mayChange=True,
        )

    @staticmethod
    def _hover(row: Any, hovered: bool, event: Any) -> None:
        """Highlight a map row when it is hovered."""
        row["frameColor"] = HOVER if hovered else ROW

    def _hover_button(self, hovered: bool, event: Any) -> None:
        """Highlight the back button when it is hovered."""
        self.back_button["frameColor"] = HOVER if hovered else ROW

    def _resize(self, window: Any, app: Any) -> None:
        """Scale the list to fit the current window."""
        if window is None:
            window = app.win
        if window is None:
            return
        aspect = window.getXSize() / max(1, window.getYSize())
        self.root.setScale(min(1.0, aspect / 1.6))

    def show(self) -> None:
        """Show the map selection menu."""
        self.root.show()

    def hide(self) -> None:
        """Hide the map selection menu."""
        self.root.hide()
