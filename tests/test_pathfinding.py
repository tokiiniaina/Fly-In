"""Tests for the single-drone pathfinding."""

import pytest

from flyin.src.connection import Connection
from flyin.src.map_data import MapData
from flyin.src.pathfinding import Graph, Path, PathFinder, find_best_path
from flyin.src.zone import Zone


def make_map(
    zones: dict[str, str],
    links: list[tuple[str, str]],
    start: str = "s",
    end: str = "e",
) -> MapData:
    """Build a map from {zone name: zone type} and a list of links."""
    data = MapData(nb_drones=1, start_hub=start, end_hub=end)
    for index, (name, kind) in enumerate(zones.items()):
        data.zones[name] = Zone(name, index, 0, zone_type=kind)
    for first, second in links:
        data.connections.append(Connection(first, second))
    return data


def best(data: MapData, start: str = "s", end: str = "e") -> Path | None:
    """Run the finder on a map (helper)."""
    return PathFinder(Graph(data)).find_path(start, end)


def test_simple_path() -> None:
    """A straight line costs one turn per zone entered."""
    data = make_map(
        {"s": "normal", "a": "normal", "e": "normal"},
        [("s", "a"), ("a", "e")],
    )
    path = best(data)
    assert path is not None
    assert path.zones == ("s", "a", "e")
    assert path.turns == 2


def test_connections_work_in_both_directions() -> None:
    """A link declared as e-s can be used from s to e."""
    data = make_map({"s": "normal", "e": "normal"}, [("e", "s")])
    path = best(data)
    assert path is not None
    assert path.zones == ("s", "e")


def test_detour_is_taken_when_cheaper() -> None:
    """The path with fewer zones is not always the fastest one.

    s-r1-r2-e has 3 moves but costs 2 + 2 + 1 = 5 turns.
    s-a-b-c-e has 4 moves but costs only 4 turns. A plain BFS (which
    counts moves) would pick the first one, Dijkstra picks the second.
    """
    data = make_map(
        {"s": "normal", "r1": "restricted", "r2": "restricted",
         "a": "normal", "b": "normal", "c": "normal", "e": "normal"},
        [("s", "r1"), ("r1", "r2"), ("r2", "e"),
         ("s", "a"), ("a", "b"), ("b", "c"), ("c", "e")],
    )
    path = best(data)
    assert path is not None
    assert path.zones == ("s", "a", "b", "c", "e")
    assert path.turns == 4


def test_restricted_zone_costs_two_turns() -> None:
    """Entering a restricted zone takes two turns."""
    data = make_map(
        {"s": "normal", "r": "restricted", "e": "normal"},
        [("s", "r"), ("r", "e")],
    )
    path = best(data)
    assert path is not None
    assert path.turns == 3


def test_blocked_zone_is_never_used() -> None:
    """A blocked zone is avoided even if it gives a shorter route."""
    data = make_map(
        {"s": "normal", "x": "blocked", "a": "normal", "b": "normal",
         "e": "normal"},
        [("s", "x"), ("x", "e"), ("s", "a"), ("a", "b"), ("b", "e")],
    )
    path = best(data)
    assert path is not None
    assert "x" not in path.zones
    assert path.turns == 3


def test_no_path_when_only_route_is_blocked() -> None:
    """If every route crosses a blocked zone, there is no path."""
    data = make_map(
        {"s": "normal", "x": "blocked", "e": "normal"},
        [("s", "x"), ("x", "e")],
    )
    assert best(data) is None


def test_no_path_when_graph_is_disconnected() -> None:
    """Two zones without any connection between them: no path."""
    data = make_map(
        {"s": "normal", "a": "normal", "e": "normal"},
        [("s", "a")],
    )
    assert best(data) is None


def test_blocked_start_or_end_gives_no_path() -> None:
    """A blocked start or end can not be entered or left."""
    blocked_end = make_map(
        {"s": "normal", "e": "blocked"}, [("s", "e")])
    blocked_start = make_map(
        {"s": "blocked", "e": "normal"}, [("s", "e")])
    assert best(blocked_end) is None
    assert best(blocked_start) is None


def test_priority_zone_wins_a_tie() -> None:
    """With the same number of turns, the priority zone is preferred."""
    data = make_map(
        {"s": "normal", "a": "normal", "p": "priority", "e": "normal"},
        [("s", "a"), ("a", "e"), ("s", "p"), ("p", "e")],
    )
    path = best(data)
    assert path is not None
    assert path.zones == ("s", "p", "e")
    assert path.turns == 2
    assert path.priority_zones == 1


def test_priority_never_beats_fewer_turns() -> None:
    """A longer route through priority zones is still slower."""
    data = make_map(
        {"s": "normal", "a": "normal", "p1": "priority",
         "p2": "priority", "p3": "priority", "e": "normal"},
        [("s", "a"), ("a", "e"),
         ("s", "p1"), ("p1", "p2"), ("p2", "p3"), ("p3", "e")],
    )
    path = best(data)
    assert path is not None
    assert path.zones == ("s", "a", "e")


def test_equal_cost_paths_give_a_stable_result() -> None:
    """Two equal paths: the same one is returned every time."""
    data = make_map(
        {"s": "normal", "a": "normal", "b": "normal", "e": "normal"},
        [("s", "b"), ("b", "e"), ("s", "a"), ("a", "e")],
    )
    results = [best(data) for _ in range(5)]
    assert all(result == results[0] for result in results)
    first = results[0]
    assert first is not None
    assert first.turns == 2
    assert first.zones == ("s", "a", "e")  # alphabetical order breaks ties


def test_start_equals_end() -> None:
    """Going from a zone to itself needs no turn."""
    data = make_map({"s": "normal"}, [], start="s", end="s")
    path = best(data, "s", "s")
    assert path is not None
    assert path.zones == ("s",)
    assert path.turns == 0


def test_unknown_zone_raises() -> None:
    """Asking for a zone that does not exist is an error."""
    data = make_map({"s": "normal", "e": "normal"}, [("s", "e")])
    with pytest.raises(ValueError, match="unknown zone"):
        best(data, "s", "nowhere")


def test_find_best_path_on_demo_map() -> None:
    """On the subject's example, the priority corridor is chosen.

    hub-corridorA(priority)-tunnelB-goal costs 3 turns, while the route
    through the restricted roof1 costs 4.
    """
    data = make_map(
        {"hub": "normal", "roof1": "restricted", "roof2": "normal",
         "corridorA": "priority", "tunnelB": "normal",
         "obstacleX": "blocked", "goal": "normal"},
        [("hub", "roof1"), ("hub", "corridorA"), ("roof1", "roof2"),
         ("roof2", "goal"), ("corridorA", "tunnelB"), ("tunnelB", "goal")],
        start="hub",
        end="goal",
    )
    path = find_best_path(data)
    assert path is not None
    assert path.zones == ("hub", "corridorA", "tunnelB", "goal")
    assert path.turns == 3
    assert path.priority_zones == 1


def test_find_best_path_needs_start_and_end() -> None:
    """A map without start or end hub is rejected."""
    with pytest.raises(ValueError, match="start_hub"):
        find_best_path(MapData())
