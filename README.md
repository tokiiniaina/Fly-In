*This project has been created as part of the 42 curriculum by tokinira.*

# Fly-in

![Fly-in 3D visualizer on the demo map](assets/demo.png)

Fly-in routes several drones from a `start_hub` to an `end_hub` in a
bidirectional network. The program parses a map, computes useful distances
with Dijkstra's algorithm, simulates all drones turn by turn, and prints the
movements required for every turn.

## Rules implemented

| Zone type | Cost and behaviour |
| --- | --- |
| `normal` | One turn to enter. |
| `priority` | One turn to enter and preferred when the cost is equal. |
| `restricted` | Two turns: takeoff, then mandatory landing on the next turn. |
| `blocked` | Never entered. |

`max_drones` limits ordinary zones. The start and end hubs are unlimited.
`max_link_capacity` is shared by both directions of a connection. Drones that
leave a zone free its place during the same turn. Waiting drones are omitted
from the output.

## Requirements

* Python 3.10 or later
* `pytest`, `flake8`, and `mypy` for development
* Panda3D only for the optional 3D viewer

No graph library is used. In particular, the project does not use
`networkx` or `graphlib`.

## Run

For isolated development, create and activate a virtual environment before
installing the dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows, activate it with `.venv\Scripts\activate` instead. The `.venv/`
directory is excluded from version control by `.gitignore`.

Run a map directly:

```bash
python3 fly_in.py maps/01_linear_path.txt
```

The output contains one line per turn:

```text
D1-waypoint1
D1-waypoint2 D2-waypoint1
D1-goal D2-waypoint2
D2-goal
```

The number of turns is printed on standard error. The optional viewer is
started with:

```bash
python3 fly_in.py maps/01_linear_path.txt --3d
```

The Makefile provides the same commands:

```bash
make install
make run
make run MAP=maps/01_linear_path.txt
make run-3d MAP=maps/01_linear_path.txt
make debug MAP=maps/01_linear_path.txt
make test
make lint
make lint-strict
make clean
```

`make run` opens the 3D game and its selectable map list. `MAP` is optional;
when provided, it selects the map shown first. `make run-3d` remains available
as an explicit alias for the 3D launch.

## Map format

```text
nb_drones: 2
start_hub: hub 0 0
end_hub: goal 3 0
hub: waypoint1 1 0 [zone=normal max_drones=1]
connection: hub-waypoint1 [max_link_capacity=1]
connection: waypoint1-goal
```

The parser validates declarations, duplicate zones and connections, unknown
zones, zone types, positive capacities, and missing hubs. Comments start with
`#`. `MapParser` is the object-oriented entry point; the old `parse_map`
function remains as a compatibility wrapper.

## Architecture

* `flyin/src/parser_function/`: map parsing and validation.
* `flyin/src/map_data.py`, `zone.py`, `connection.py`: simple data models.
* `flyin/src/engine/distances.py`: reverse Dijkstra distance map.
* `flyin/src/engine/simulator.py`: small greedy multi-drone simulator.
* `flyin/src/engine/checker.py`: independent output replay and validation.
* `scripts/benchmark.py`: official-map benchmark with checker validation.
* `viz3d/`: optional Panda3D scene adapter and viewer.
* `assets/models/`: reusable Panda3D BAM models for the drone, zone styles,
  sky and distant mesas.
* `assets/ui/`: PNG sprites used by the zone-type legend.
* `tests/`: parser, simulator, checker, and viewer tests.

## Algorithm and complexity

The distance map runs Dijkstra backwards from the end hub. A drone chooses a
reachable neighbour with a strictly smaller remaining distance. Among equal
cost choices, priority zones are preferred, then the route with the higher
capacity across its next link and destination zone. The simulator then applies
link and zone capacities for the current turn.

For `V` zones and `E` connections, Dijkstra uses `O((V + E) log V)` time and
`O(V + E)` memory. Each simulation turn scans the drones and their neighbours,
so one turn costs `O(D + E)` in the simple implementation. The distance map
is computed once and reused; no complete path table is cached.

The simulator has a turn limit and raises a clear error when the end hub is
unreachable or the simulation cannot finish. Strictly decreasing distances
avoid cycles and dead-end loops. The independent checker replays every
movement without using the simulator's counters.

## Performance

Measured locally with `python3 scripts/benchmark.py`:

| Map | Drones | Turns | Target | Status |
| --- | ---: | ---: | ---: | --- |
| `01_linear_path.txt` | 2 | 4 | 6 | OK |
| `02_simple_fork.txt` | 4 | 4 | 8 | OK |
| `03_basic_capacity.txt` | 4 | 4 | 6 | OK |
| `01_dead_end_trap.txt` | 5 | 8 | 12 | OK |
| `02_circular_loop.txt` | 6 | 15 | 15 | OK |
| `03_priority_puzzle.txt` | 5 | 7 | 12 | OK |
| `01_maze_nightmare.txt` | 8 | 13 | 30 | OK |
| `02_capacity_hell.txt` | 12 | 16 | 35 | OK |
| `03_ultimate_challenge.txt` | 15 | 26 | 45 | OK |
| `01_the_impossible_dream.txt` | 25 | 43 | 45 | OK |

The benchmark status is `OK` only when the turn target and the independent
`OutputChecker` both pass.

## Quality checks

```bash
python3 -m pytest -q
python3 -m flake8 .
python3 -m mypy --warn-return-any --warn-unused-ignores \
    --ignore-missing-imports --disallow-untyped-defs \
    --check-untyped-defs .
```

## Resources and use of AI

* [Dijkstra's algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
* [Python documentation](https://docs.python.org/3/)
* [Panda3D documentation](https://docs.panda3d.org/)

An AI assistant was used as a programming mentor for code review, test ideas,
documentation, and debugging. All changes were checked against the subject,
the project's tests, and the required linters.
