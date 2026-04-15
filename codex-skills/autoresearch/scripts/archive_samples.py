#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def copy_into(source: Path, dest_dir: Path) -> str:
    target = dest_dir / source.name
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    if source.is_dir():
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    return str(target)


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive raw sample outputs into an autoresearch run directory.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch run directory")
    parser.add_argument("--experiment-id", required=True, type=int, help="Experiment number")
    parser.add_argument("--source", action="append", required=True, help="File or directory to archive; repeatable")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    dest_dir = run_dir / "outputs" / f"experiment-{args.experiment_id}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for item in args.source:
        source = Path(item).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"Source does not exist: {source}")
        copied.append(copy_into(source, dest_dir))

    print("\n".join(copied))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
