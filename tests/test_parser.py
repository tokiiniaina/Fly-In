"""Tests for the map parser."""

from pathlib import Path

import pytest

from flyin.src.parser_function import parse_map


def write_map(tmp_path: Path, content: str) -> str:
    """Write a map file in a temporary folder and return its path."""
    file = tmp_path / "map.txt"
    file.write_text(content, encoding="utf-8")
    return str(file)


def test_valid_map(tmp_path: Path) -> None:
    """A simple valid map is parsed correctly."""
    path = write_map(
        tmp_path,
        "nb_drones: 2\n"
        "start_hub: s 0 0\n"
        "end_hub: e 1 1\n"
        "connection: s-e\n",
    )
    map_data = parse_map(path)
    assert map_data.nb_drones == 2
    assert map_data.start_hub == "s"
    assert map_data.end_hub == "e"
    assert len(map_data.connections) == 1


def test_reversed_duplicate_connection(tmp_path: Path) -> None:
    """The connections s-e and e-s are the same link."""
    path = write_map(
        tmp_path,
        "nb_drones: 2\n"
        "start_hub: s 0 0\n"
        "end_hub: e 1 1\n"
        "connection: s-e\n"
        "connection: e-s\n",
    )
    with pytest.raises(ValueError, match="duplicate connection"):
        parse_map(path)


def test_start_hub_capacity_is_ignored(tmp_path: Path) -> None:
    """max_drones on start_hub is ignored, even if invalid."""
    path = write_map(
        tmp_path,
        "nb_drones: 2\n"
        "start_hub: s 0 0 [max_drones=abc]\n"
        "end_hub: e 1 1\n"
        "connection: s-e\n",
    )
    map_data = parse_map(path)
    assert map_data.start_hub == "s"


HEADER = "nb_drones: 2\n"
ZONES = "start_hub: s 0 0\nend_hub: e 1 1\n"

NEGATIVE_CASES = [
    ("unknown_declaration",
     HEADER + ZONES + "foo: bar\n",
     "unknown declaration"),
    ("connection_to_missing_zone",
     HEADER + ZONES + "connection: s-x\n",
     "unknown zone"),
    ("connection_before_zones",
     HEADER + "connection: s-e\n" + ZONES,
     "unknown zone"),
    ("duplicate_zone",
     HEADER + ZONES + "hub: s 2 2\n",
     "duplicate zone name"),
    ("two_start_hubs",
     HEADER + ZONES + "start_hub: t 3 3\n",
     "duplicate start_hub"),
    ("invalid_zone_type",
     HEADER + ZONES + "hub: a 2 2 [zone=lava]\n",
     "invalid zone type"),
    ("max_drones_zero",
     HEADER + ZONES + "hub: a 2 2 [max_drones=0]\n",
     "must be positive"),
    ("negative_nb_drones",
     "nb_drones: -2\n" + ZONES,
     "must be positive"),
]


@pytest.mark.parametrize(
    "content, expected",
    [case[1:] for case in NEGATIVE_CASES],
    ids=[case[0] for case in NEGATIVE_CASES],
)
def test_invalid_maps(tmp_path: Path, content: str, expected: str) -> None:
    """Invalid maps are rejected with a clear error message."""
    path = write_map(tmp_path, content)
    with pytest.raises(ValueError, match=expected):
        parse_map(path)


def test_inline_comments_are_ignored(tmp_path: Path) -> None:
    """Text after a # is a comment, even after a declaration."""
    path = write_map(
        tmp_path,
        "# full line comment\n"
        "nb_drones: 2  # two drones\n"
        "start_hub: s 0 0  # the start\n"
        "end_hub: e 1 1\n"
        "connection: s-e  # a link\n",
    )
    map_data = parse_map(path)
    assert map_data.nb_drones == 2
    assert map_data.start_hub == "s"
    assert len(map_data.connections) == 1
