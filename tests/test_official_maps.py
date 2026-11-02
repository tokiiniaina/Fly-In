"""Tests on the official maps of the subject."""

from pathlib import Path

import pytest

from flyin.src.parser_function import parse_map
from flyin.src.pathfinding import find_best_path

MAPS = Path(__file__).resolve().parent.parent / "maps"

# (file, nb_drones, nb_zones, best turns for ONE drone alone)
OFFICIAL_MAPS = [
    ("01_dead_end_trap.txt", 5, 6, 4),
    ("01_linear_path.txt", 2, 4, 3),
    ("01_maze_nightmare.txt", 8, 17, 6),
    ("01_the_impossible_dream.txt", 25, 54, 19),
    ("02_capacity_hell.txt", 12, 15, 5),
    ("02_circular_loop.txt", 6, 7, 5),
    ("02_simple_fork.txt", 4, 5, 3),
    ("03_basic_capacity.txt", 4, 4, 3),
    ("03_priority_puzzle.txt", 5, 7, 4),
    ("03_ultimate_challenge.txt", 15, 31, 12),
]


@pytest.mark.parametrize(
    "name, drones, zones, turns",
    OFFICIAL_MAPS,
    ids=[entry[0] for entry in OFFICIAL_MAPS],
)
def test_official_map(name: str, drones: int, zones: int,
                      turns: int) -> None:
    """Each official map is parsed and has a valid best path."""
    data = parse_map(str(MAPS / name))
    assert data.nb_drones == drones
    assert len(data.zones) == zones
    path = find_best_path(data)
    assert path is not None
    assert path.turns == turns
