#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def resolve_candidate(run_dir: Path, override: str | None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    results_json = run_dir / "results.json"
    if results_json.exists():
        payload = json.loads(results_json.read_text(encoding="utf-8"))
        candidate_name = payload.get("candidate_file")
        if candidate_name:
            return run_dir / candidate_name
    matches = [path for path in run_dir.glob("*.md") if path.name not in {"SKILL.md.baseline", "run-spec.md", "changelog.md", "mutations.md"}]
    if not matches:
        raise SystemExit("Could not determine candidate file; pass --candidate-file explicitly")
    return matches[0]


def append_mutation_row(run_dir: Path, experiment_id: int, status: str, note: str, snapshot: str) -> None:
    mutations_md = run_dir / "mutations.md"
    row = f"| {experiment_id} | {status} | {note.replace('|', '/')} | `{snapshot}` |\n"
    if mutations_md.exists():
        existing = mutations_md.read_text(encoding="utf-8")
        atomic_write(mutations_md, existing + row)
    else:
        atomic_write(
            mutations_md,
            "# Mutation log\n\n| Experiment | Status | Mutation | Candidate snapshot |\n| --- | --- | --- | --- |\n" + row,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and snapshot a mutated candidate for an autoresearch experiment.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch run directory")
    parser.add_argument("--experiment-id", required=True, type=int, help="Experiment number")
    parser.add_argument("--mutation-note", required=True, help="Short note describing the mutation")
    parser.add_argument("--candidate-file", default=None, help="Optional path to the run's candidate file")
    parser.add_argument("--source-file", default=None, help="Optional full file to copy over the current candidate")
    parser.add_argument("--find", default=None, help="Optional exact text to replace")
    parser.add_argument("--replace-with", default=None, help="Replacement text when using --find")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    candidate_file = resolve_candidate(run_dir, args.candidate_file)
    if not candidate_file.exists():
        raise SystemExit(f"Candidate file does not exist: {candidate_file}")

    history_dir = run_dir / "candidate-history"
    history_dir.mkdir(parents=True, exist_ok=True)
    before_snapshot = history_dir / f"experiment-{args.experiment_id}-before.md"
    working_snapshot = history_dir / f"experiment-{args.experiment_id}-working.md"
    shutil.copy2(candidate_file, before_snapshot)

    if args.source_file:
        source = Path(args.source_file).expanduser().resolve()
        if not source.exists():
            raise SystemExit(f"Source file does not exist: {source}")
        shutil.copy2(source, candidate_file)
    elif args.find is not None:
        if args.replace_with is None:
            raise SystemExit("--replace-with is required when using --find")
        content = candidate_file.read_text(encoding="utf-8")
        if args.find not in content:
            raise SystemExit("Could not find the requested text in the candidate file")
        atomic_write(candidate_file, content.replace(args.find, args.replace_with, 1))
    else:
        raise SystemExit("Provide either --source-file or --find/--replace-with")

    shutil.copy2(candidate_file, working_snapshot)
    append_mutation_row(run_dir, args.experiment_id, "prepared", args.mutation_note, working_snapshot.name)
    print(
        json.dumps(
            {
                "candidate_file": str(candidate_file),
                "before_snapshot": str(before_snapshot),
                "working_snapshot": str(working_snapshot),
                "mutation_note": args.mutation_note,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
