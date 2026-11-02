"""Run the simulator and the checker on every official map."""

from pathlib import Path

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function import parse_map

TARGETS = {
    "01_linear_path": 6, "02_simple_fork": 8, "03_basic_capacity": 6,
    "01_dead_end_trap": 12, "02_circular_loop": 15,
    "03_priority_puzzle": 12, "01_maze_nightmare": 30,
    "02_capacity_hell": 35, "03_ultimate_challenge": 45,
    "01_the_impossible_dream": 45,
}


def main() -> None:
    """Print turns, target and checker verdict for each map."""
    for path in sorted(Path("maps").glob("*.txt")):
        data = parse_map(str(path))
        lines = Simulator(data).run()
        try:
            OutputChecker(parse_map(str(path))).check(lines)
            verdict = "valid"
        except ValueError as error:
            verdict = f"INVALID: {error}"
        target = TARGETS.get(path.stem, 0)
        print(f"{path.stem:28} {len(lines):3} turns "
              f"(target {target}) {verdict}")


if __name__ == "__main__":
    main()
