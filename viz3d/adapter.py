"""Turns a parsed map and the output lines into what the 3D viewer reads.

No panda3d is imported here, so this module is testable without a window.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from flyin.src.map_data import MapData

from .contract import (
    Connection, DroneSnapshot, Graph, Movement, TurnResult, Zone, ZoneType,
)


class InvalidReplay(ValueError):
    """Raised when the output lines cannot be replayed on the map."""


def to_graph(data: MapData) -> Graph:
    """Convert the parsed map to the viewer's ``Graph``."""
    graph = Graph(nb_drones=data.nb_drones)
    for zone in data.zones.values():
        graph.add_zone(Zone(
            name=zone.name, x=zone.x, y=zone.y,
            zone_type=ZoneType(zone.zone_type),
            color=None if zone.color == "none" else zone.color,
            max_drones=zone.max_drones,
            is_start=zone.name == data.start_hub,
            is_end=zone.name == data.end_hub,
        ))
    for conn in data.connections:
        graph.add_connection(
            Connection(conn.zone1, conn.zone2, conn.max_link_capacity))
    return graph


def _links(data: MapData) -> Dict[frozenset[str], str]:
    """Link name (file order) for every pair of zones."""
    return {frozenset((c.zone1, c.zone2)): f"{c.zone1}-{c.zone2}"
            for c in data.connections}


def to_turns(data: MapData, lines: List[str]) -> List[TurnResult]:
    """Replay the output lines and build one ``TurnResult`` per turn."""
    assert data.start_hub is not None and data.end_hub is not None
    end = data.end_hub
    links = _links(data)
    by_name = {name: key for key, name in links.items()}
    zone_of: Dict[int, str | None] = {
        d: data.start_hub
        for d in range(1, data.nb_drones + 1)
    }
    flight: Dict[int, Tuple[str, str]] = {}
    results: List[TurnResult] = []
    for number, line in enumerate(lines, start=1):
        result = TurnResult(number)
        for token in line.split():
            drone_text, _, target = token[1:].partition("-")
            drone = int(drone_text)
            if drone in flight:                        # landing
                src, dst = flight.pop(drone)
                result.movements.append(Movement(
                    drone, src, dst, False, links[frozenset((src, dst))]))
                zone_of[drone] = dst
            elif target in data.zones:                 # ordinary move
                current_zone = zone_of[drone]
                if current_zone is None:
                    raise InvalidReplay(f"turn {number}: {token}")
                result.movements.append(Movement(
                    drone, current_zone, target, False,
                    links[frozenset((current_zone, target))]))
                zone_of[drone] = target
            elif target in by_name:                    # take-off
                a, b = sorted(
                    by_name[target],
                    key=lambda zone: zone != zone_of[drone],
                )
                flight[drone] = (a, b)
                result.movements.append(Movement(
                    drone, a, b, True, target))
                zone_of[drone] = None
            else:
                raise InvalidReplay(f"turn {number}: unknown '{token}'")
        for drone in range(1, data.nb_drones + 1):
            if drone in flight:
                src, dst = flight[drone]
                result.snapshots[drone] = DroneSnapshot(
                    drone, None, src, dst)
            else:
                zone = zone_of[drone]
                result.snapshots[drone] = DroneSnapshot(
                    drone, zone, delivered=zone == end)
        result.delivered = sum(
            1 for s in result.snapshots.values() if s.delivered)
        results.append(result)
    return results


def build_scene_data(data: MapData, lines: List[str]
                     ) -> Tuple[Graph, List[TurnResult]]:
    """Everything the 3D viewer needs."""

    return to_graph(data), to_turns(data, lines)
