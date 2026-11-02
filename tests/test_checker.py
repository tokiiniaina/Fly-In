"""Tests for the independent output checker."""

import pytest

from flyin.src.connection import Connection
from flyin.src.engine.checker import OutputChecker
from flyin.src.map_data import MapData
from flyin.src.zone import Zone


def make_map(
    zones: dict[str, Zone],
    connections: list[Connection],
    drones: int = 1,
) -> MapData:
    """Build a small map for one checker test."""
    return MapData(
        nb_drones=drones,
        zones=zones,
        connections=connections,
        start_hub="start",
        end_hub="end",
    )


def test_valid_output_is_accepted() -> None:
    """A valid sequence reaches the end zone."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "middle": Zone("middle", 1, 0),
            "end": Zone("end", 2, 0),
        },
        [
            Connection("start", "middle"),
            Connection("middle", "end"),
        ],
    )

    OutputChecker(data).check(["D1-middle", "D1-end"])


def test_zone_capacity_is_checked() -> None:
    """Two drones cannot finish in a one-place zone."""
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

    with pytest.raises(ValueError, match="zone 'middle'"):
        OutputChecker(data).check(
            ["D1-middle D2-middle", "D1-end D2-end"]
        )


def test_link_capacity_is_checked() -> None:
    """Two drones cannot use a one-place link together."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "end": Zone("end", 1, 0),
        },
        [Connection("start", "end", 1)],
        drones=2,
    )

    with pytest.raises(ValueError, match="link"):
        OutputChecker(data).check(["D1-end D2-end"])


def test_restricted_landing_is_required() -> None:
    """A restricted flight must be followed by its landing."""
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

    with pytest.raises(ValueError, match="must land"):
        OutputChecker(data).check(["D1-start-restricted", "D1-end"])


def test_restricted_drone_cannot_wait_on_the_link() -> None:
    """A restricted flight must land on the immediately following turn."""
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

    with pytest.raises(ValueError, match="must land"):
        OutputChecker(data).check(
            ["D1-start-restricted", "", "D1-restricted", "D1-end"]
        )


def test_blocked_or_disconnected_move_is_rejected() -> None:
    """A move to a blocked or disconnected zone is rejected."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "blocked": Zone("blocked", 1, 0, zone_type="blocked"),
            "end": Zone("end", 2, 0),
        },
        [Connection("start", "blocked")],
    )

    with pytest.raises(ValueError, match="blocked"):
        OutputChecker(data).check(["D1-blocked"])


def test_undelivered_drone_is_rejected() -> None:
    """The checker rejects output that stops before delivery."""
    data = make_map(
        {
            "start": Zone("start", 0, 0),
            "end": Zone("end", 1, 0),
        },
        [Connection("start", "end")],
    )

    with pytest.raises(ValueError, match="not delivered"):
        OutputChecker(data).check([])
