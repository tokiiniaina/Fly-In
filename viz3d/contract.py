"""Data shapes read by the 3D viewer (no panda3d and no rules in here).

The viewer never looks at the parser or at the simulation directly. It only
needs a ``Graph`` (the map) and a list of ``TurnResult`` (what happened at
each turn). ``viz3d.adapter`` builds both from our validated data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional


class ZoneType(Enum):
    """Kind of zone, which decides how the viewer draws it."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


@dataclass(frozen=True)
class Zone:
    """A node of the network."""

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: Optional[str] = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def capacity(self) -> Optional[int]:
        """Capacity limit, or None when unlimited (start and end)."""
        if self.is_start or self.is_end:
            return None
        return self.max_drones


@dataclass(frozen=True)
class Connection:
    """A bidirectional edge between two zones."""

    a: str
    b: str
    max_link_capacity: int = 1

    @property
    def key(self) -> FrozenSet[str]:
        """Order independent identity of the connection."""
        return frozenset((self.a, self.b))

    @property
    def name(self) -> str:
        """Name used as a key by the viewer, e.g. ``roof1-roof2``."""
        return f"{self.a}-{self.b}"

    def other(self, zone: str) -> str:
        """Return the zone at the other end of the connection."""
        return self.b if zone == self.a else self.a


@dataclass
class Graph:
    """The whole network: zones, connections and drone count."""

    nb_drones: int = 0
    zones: Dict[str, Zone] = field(default_factory=dict)
    connections: List[Connection] = field(default_factory=list)
    _adjacency: Dict[str, List[Connection]] = field(
        default_factory=dict, repr=False
    )

    def add_zone(self, zone: Zone) -> None:
        """Register a zone."""
        self.zones[zone.name] = zone
        self._adjacency.setdefault(zone.name, [])

    def add_connection(self, conn: Connection) -> None:
        """Register a connection between two known zones."""
        self.connections.append(conn)
        self._adjacency[conn.a].append(conn)
        self._adjacency[conn.b].append(conn)

    def neighbors(self, name: str) -> List[Connection]:
        """Connections touching a zone."""
        return self._adjacency.get(name, [])

    @property
    def start(self) -> Zone:
        """The unique start zone."""
        return next(z for z in self.zones.values() if z.is_start)

    @property
    def end(self) -> Zone:
        """The unique end zone."""
        return next(z for z in self.zones.values() if z.is_end)


@dataclass(frozen=True)
class Movement:
    """What one drone does during one turn."""

    drone_id: int
    src: str
    dst: str
    in_transit: bool
    connection: str

    @property
    def label(self) -> str:
        """Output token such as ``D1-roof1`` or ``D1-roof1-roof2``."""
        target = self.connection if self.in_transit else self.dst
        return f"D{self.drone_id}-{target}"


@dataclass(frozen=True)
class DroneSnapshot:
    """Where a drone is at the end of a turn."""

    drone_id: int
    zone: Optional[str]
    transit_from: Optional[str] = None
    transit_to: Optional[str] = None
    delivered: bool = False


@dataclass
class TurnResult:
    """Everything that happened during one turn."""

    turn: int
    movements: List[Movement] = field(default_factory=list)
    snapshots: Dict[int, DroneSnapshot] = field(default_factory=dict)
    delivered: int = 0
