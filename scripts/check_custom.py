"""Run simulator and checker on the custom maps."""

from pathlib import Path
import time

from flyin.src.engine.checker import OutputChecker
from flyin.src.engine.simulator import Simulator
from flyin.src.parser_function import parse_map


def main() -> None:
    """Print the result of every custom map."""
    for path in sorted(Path("maps/custom").glob("*.txt")):
        start = time.time()
        try:
            data = parse_map(str(path))
            lines = Simulator(data).run()
            OutputChecker(parse_map(str(path))).check(lines)
            result = f"{len(lines)} turns, valid"
        except ValueError as error:
            result = f"error (clean): {error}"
        except Exception as error:
            result = f"CRASH {type(error).__name__}: {error}"
        print(f"{path.stem:22} {result} "
              f"[{time.time() - start:.2f}s]")


if __name__ == "__main__":
    main()
