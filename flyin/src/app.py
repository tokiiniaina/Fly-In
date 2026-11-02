"""Command line of Fly-in."""

import argparse
import sys
from pathlib import Path

from flyin.src.engine.simulator import Simulator
from flyin.src.map_data import MapData
from flyin.src.parser_function import MapParser


class Application:
    """Parse the map, simulate, print the turns."""

    @staticmethod
    def _parser() -> argparse.ArgumentParser:
        """Create the argument parser."""
        parser = argparse.ArgumentParser(prog="fly_in.py")
        parser.add_argument("map", help="path of the map file")
        parser.add_argument("--3d", dest="three_d", action="store_true",
                            help="open the 3D viewer")
        return parser

    @staticmethod
    def _show_3d(
        data: MapData,
        lines: list[str],
        name: str,
        map_path: str,
    ) -> int:
        """Open the 3D viewer and return an exit code."""
        try:
            from viz3d.launcher import show3d
            show3d(data, lines, name, map_path)
        except ImportError as error:
            print(f"Error: cannot start the 3D viewer: {error}",
                  file=sys.stderr)
            return 1
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        return 0

    def run(self, argv: list[str] | None = None) -> int:
        """Run the program and return the exit code."""
        args = self._parser().parse_args(argv)
        try:
            data = MapParser().parse(args.map)
            lines = Simulator(data).run()
        except OSError as error:
            print(f"Error: cannot read '{error.filename}'",
                  file=sys.stderr)
            return 1
        except ValueError as error:
            print(f"Error: {error}", file=sys.stderr)
            return 1
        print("\n".join(lines))
        print(f"{len(lines)} turns", file=sys.stderr)
        if args.three_d:
            return self._show_3d(
                data, lines, Path(args.map).name,
                str(Path(args.map).resolve()),
            )

        return 0
