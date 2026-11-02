"""Tests for the greedy drone simulator."""

import pytest

from flyin.src.connection import Connection
from flyin.src.engine.simulator import Simulator
from flyin.src.map_data import MapData
from flyin.src.zone import Zone


def make_map(
    zones: dict[str, Zone],
    connections: list[Connection],
    drones: int = 1,
) -> MapData:
    """Build a small map for one simulator test."""
    return MapData(
        nb_drones=drones,
        zones=zones,
        connections=connections,
        start_hub="start",
        end_hub="end",
    )


def test_zone_capacity_is_respected() -> None:
    """A full zone delays the next drone."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "middle": Zone("middle", 1, 0, max_drones=1),
            "end": Zone("end", 2, 0),
        },
        [
            Connection("start", "middle", 2),
            Connection("middle", "end", 2),
        ],
        drones=2,
    )

    lines = Simulator(data).run()

    assert len(lines) == 3


def test_link_capacity_is_respected() -> None:
    """A link capacity of one serializes two drones."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "end": Zone("end", 1, 0),
        },
        [Connection("start", "end", 1)],
        drones=2,
    )

    lines = Simulator(data).run()

    assert lines == ["D1-end", "D2-end"]


def test_restricted_zone_takes_two_turns() -> None:
    """A restricted destination requires takeoff and landing."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "restricted": Zone(
                "restricted", 1, 0, zone_type="restricted"
            ),
            "end": Zone("end", 2, 0),
        },
        [
            Connection("start", "restricted"),
            Connection("restricted", "end"),
        ],
    )

    lines = Simulator(data).run()

    assert lines == [
        "D1-start-restricted",
        "D1-restricted",
        "D1-end",
    ]


def test_priority_zone_is_preferred_when_cost_is_equal() -> None:
    """The simulator chooses a priority zone over a normal zone."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "normal": Zone("normal", 1, 1, max_drones=1),
            "priority": Zone(
                "priority", 1, -1,
                zone_type="priority",
                max_drones=1,
            ),
            "end": Zone("end", 2, 0),
        },
        [
            Connection("start", "normal"),
            Connection("normal", "end"),
            Connection("start", "priority"),
            Connection("priority", "end"),
        ],
    )

    lines = Simulator(data).run()

    assert lines[0] == "D1-priority"


def test_higher_capacity_route_is_preferred_when_cost_is_equal() -> None:
    """Equal-cost routes prefer the one with more available capacity."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "narrow": Zone("narrow", 1, 1, max_drones=3),
            "wide": Zone("wide", 1, -1, max_drones=3),
            "end": Zone("end", 2, 0),
        },
        [
            Connection("start", "narrow", 1),
            Connection("narrow", "end", 3),
            Connection("start", "wide", 3),
            Connection("wide", "end", 3),
        ],
        drones=2,
    )

    lines = Simulator(data).run()

    assert lines[0] == "D1-wide D2-wide"


def test_blocked_zone_is_not_used() -> None:
    """A blocked zone cannot be part of the selected path."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "blocked": Zone(
                "blocked", 1, 0, zone_type="blocked"
            ),
            "end": Zone("end", 2, 0),
        },
        [
            Connection("start", "blocked"),
            Connection("blocked", "end"),
        ],
    )

    with pytest.raises(ValueError, match="cannot be reached"):
        Simulator(data).run()


def test_dead_end_is_not_selected() -> None:
    """A dead-end branch is ignored when it cannot reach the end."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "dead_end": Zone("dead_end", 1, 1),
            "middle": Zone("middle", 1, 0),
            "end": Zone("end", 2, 0),
        },
        [
            Connection("start", "dead_end"),
            Connection("start", "middle"),
            Connection("middle", "end"),
        ],
    )

    lines = Simulator(data).run()

    assert lines == ["D1-middle", "D1-end"]


def test_no_path_raises_a_clear_error() -> None:
    """A map without a route raises a clear error."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "end": Zone("end", 1, 0),
        },
        [],
    )

    with pytest.raises(ValueError, match="cannot be reached"):

        Simulator(data).run()
