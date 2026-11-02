"""Tests for the adapter used by the Panda3D viewer."""

from pathlib import Path

from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function.map import parse_map
from viz3d.adapter import build_scene_data


ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "demo.txt"


def test_demo_simulation_is_converted_for_3d() -> None:
    """The demo stays within six turns and delivers every drone."""
    data = parse_map(str(DEMO))
    lines = Simulator(data).run()

    graph, turns = build_scene_data(data, lines)

    delivered = [turn.delivered for turn in turns]

    assert graph.nb_drones == data.nb_drones
    assert len(turns) <= 6
    assert delivered == sorted(delivered)
    assert delivered[-1] == data.nb_drones
    assert all(snapshot.delivered

               for snapshot in turns[-1].snapshots.values())
