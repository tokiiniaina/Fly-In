from dataclasses import dataclass


@dataclass
class Zone:
    """Represent a zone of the drone network."""

    name:        str
    x:           int
    y:           int
    zone_type:   str = "normal"
    color:       str = "none"
    max_drones:  int = 1
