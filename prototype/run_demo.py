"""Run the reviewed-change DXF propagation slice on synthetic inputs."""

import argparse
from pathlib import Path

from propagate.core import apply_approved_move


def main() -> None:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changes", type=Path, default=root / "out" / "changes.json")
    parser.add_argument("--samples", type=Path, default=root / "samples")
    parser.add_argument("--sidecars", type=Path, default=root / "out")
    parser.add_argument("--output", type=Path, default=root / "out" / "propagated")
    args = parser.parse_args()
    for result in apply_approved_move(args.changes, args.samples, args.sidecars, args.output):
        print(f"{result.sheet}: {result.before} -> {result.after} mm")
    print(f"Report: {args.output / 'report.md'}")


if __name__ == "__main__":
    main()
