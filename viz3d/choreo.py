"""Turns engine turns into per-drone animation steps (no rendering here).

The renderer only replays what this module derives from the real
``TurnResult`` list, so every animation matches a simulation decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set

from .contract import Graph, TurnResult


class Phase(Enum):
    """What a drone does during one turn."""

    IDLE = "idle"
    WALK = "walk"
    ENTER = "enter"      # first half of a restricted move (in transit)
    EXIT = "exit"        # second half: lands on the restricted zone
    ARRIVE = "arrive"    # final move into the end zone


@dataclass(frozen=True)
class Step:
    """One drone during one turn.

    ``t0`` and ``t1`` are fractions of the route from ``src`` to ``dst``
    covered at the start and at the end of the turn.
    """

    drone_id: int
    phase: Phase
    src: str
    dst: str
    connection: Optional[str]
    t0: float
    t1: float
    src_slot: int
    dst_slot: int


class Choreography:
    """Per-turn animation steps and stable standing slots."""

    def __init__(self, graph: Graph, turns: List[TurnResult]) -> None:
        """Derive the steps of every turn."""
        self.graph = graph
        self.layout: Dict[str, int] = {}
        for zone in graph.zones.values():
            cap = zone.capacity
            self.layout[zone.name] = graph.nb_drones if cap is None else cap
        self.steps: List[Dict[int, Step]] = []
        self._build(turns)

    def initial_slot(self, drone_id: int) -> int:
        """Slot of a drone on the start pad before turn 1."""
        return drone_id - 1

    def _build(self, turns: List[TurnResult]) -> None:
        graph = self.graph
        where: Dict[int, str] = {
            d: graph.start.name for d in range(1, graph.nb_drones + 1)
        }
        slot: Dict[int, int] = {
            d: self.initial_slot(d) for d in where
        }
        flight: Dict[int, int] = {}
        for result in turns:
            moves = {m.drone_id: m for m in result.movements}
            staying: Dict[str, Set[int]] = {}
            leaving: Dict[str, Set[int]] = {}
            for drone, zone in where.items():
                if drone in moves:
                    leaving.setdefault(zone, set()).add(slot[drone])
                else:
                    staying.setdefault(zone, set()).add(slot[drone])
            taken: Dict[str, Set[int]] = {}
            step_map: Dict[int, Step] = {}
            for drone in range(1, graph.nb_drones + 1):
                zone, here = where[drone], slot[drone]
                mv = moves.get(drone)
                if mv is None:
                    step_map[drone] = Step(drone, Phase.IDLE, zone, zone,
                                           None, 0.0, 0.0, here, here)
                    continue
                if mv.in_transit:
                    flight[drone] = here
                    step_map[drone] = Step(drone, Phase.ENTER, mv.src,
                                           mv.dst, mv.connection, 0.0, 0.5,
                                           here, here)
                    continue
                new_slot = self._free_slot(
                    mv.dst, staying, leaving, taken)
                if drone in flight:
                    src_slot = flight.pop(drone)
                    phase, t0 = Phase.EXIT, 0.5
                else:
                    src_slot = here
                    phase = Phase.ARRIVE if mv.dst == graph.end.name \
                        else Phase.WALK
                    t0 = 0.0
                step_map[drone] = Step(drone, phase, mv.src, mv.dst,
                                       mv.connection, t0, 1.0, src_slot,
                                       new_slot)
                where[drone] = mv.dst
                slot[drone] = new_slot
            for drone, mv in moves.items():
                if mv.in_transit:
                    where[drone] = where[drone]
            self.steps.append(step_map)

    def _free_slot(self, zone: str, staying: Dict[str, Set[int]],
                   leaving: Dict[str, Set[int]],
                   taken: Dict[str, Set[int]]) -> int:
        used = staying.get(zone, set()) | taken.get(zone, set())
        pending = leaving.get(zone, set())
        size = self.layout[zone]
        order = [i for i in range(size) if i not in used]
        pick = next((i for i in order if i not in pending),
                    order[0] if order else 0)
        taken.setdefault(zone, set()).add(pick)
        return pick
