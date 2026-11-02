"""Benchmark the current simulator on all official maps."""

from pathlib import Path
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flyin.src.engine.checker import OutputChecker  # noqa: E402
from flyin.src.engine.simulator import Simulator  # noqa: E402
from flyin.src.parser_function.map import MapParser  # noqa: E402


TARGETS: dict[str, int] = {
    "01_linear_path.txt": 6,
    "02_simple_fork.txt": 8,
    "03_basic_capacity.txt": 6,
    "01_dead_end_trap.txt": 12,
    "02_circular_loop.txt": 15,
    "03_priority_puzzle.txt": 12,
    "01_maze_nightmare.txt": 30,
    "02_capacity_hell.txt": 35,
    "03_ultimate_challenge.txt": 45,
    "01_the_impossible_dream.txt": 45,
}


class Benchmark:
    """Run the simulator and print one result per official map."""

    def __init__(self, maps_directory: Path) -> None:
        """Store the directory containing the official maps."""
        self._maps_directory = maps_directory

    def run(self) -> None:
        """Run the simulator for every official map."""
        print(
            f"{'Map':<30} "
            f"{'Drones':>6} "
            f"{'Turns':>6} "
            f"{'Target':>6} "
            f"{'Status':<6} "
            f"{'Time (s)':>10}"
        )
        print("-" * 72)

        for map_path in sorted(self._maps_directory.glob("*.txt")):
            self._run_map(map_path)

    def _run_map(self, map_path: Path) -> None:
        """Run one map and print its benchmark result."""
        start = perf_counter()

        try:
            data = MapParser().parse(str(map_path))
            lines = Simulator(data).run()
            OutputChecker(data).check(lines)
            turns = len(lines)
            target = TARGETS.get(map_path.name)
            status = self._status(map_path.name, turns)
            drones = data.nb_drones
        except (OSError, ValueError) as error:
            elapsed = perf_counter() - start
            print(
                f"{map_path.name:<30} "
                f"{'-':>6} "
                f"{'-':>6} "
                f"{'-':>6} "
                f"{'KO':<6} "
                f"{elapsed:>10.4f}"
            )
            print(f"  Error: {error}")
            return

        elapsed = perf_counter() - start
        target_text = str(target) if target is not None else "-"
        print(
            f"{map_path.name:<30} "
            f"{drones:>6} "
            f"{turns:>6} "
            f"{target_text:>6} "
            f"{status:<6} "
            f"{elapsed:>10.4f}"
        )

    @staticmethod
    def _status(map_name: str, turns: int) -> str:
        """Return OK when the measured result reaches its target."""
        target = TARGETS.get(map_name)
        if target is None:
            return "N/A"
        return "OK" if turns <= target else "KO"


def main() -> None:
    """Run the benchmark from the project root."""
    maps_directory = PROJECT_ROOT / "maps"
    Benchmark(maps_directory).run()


if __name__ == "__main__":
    main()
