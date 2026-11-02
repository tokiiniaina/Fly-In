"""Opens the Panda3D window for a simulation.

``panda3d`` is imported only when ``show3d`` is called, so the rest of the
project works on machines where Panda3D is not installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from flyin.src.map_data import MapData

from .adapter import build_scene_data


def show3d(
    data: MapData,
    lines: List[str],
    map_name: str = "map",
    map_path: str | None = None,
) -> None:
    """Show the simulation in 3D (ImportError if Panda3D is missing)."""
    graph, turns = build_scene_data(data, lines)
    from .app import FlyInApp

    path = Path(map_path) if map_path is not None else None
    directory = path.parent if path is not None else None
    filename = path.name if path is not None else map_name
    FlyInApp(
        graph,
        turns,
        map_name=map_name,
        map_directory=directory,
        map_file=filename,
    ).run()
