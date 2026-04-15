#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {}


def render_template(template: str, context: dict[str, object]) -> str:
    safe = {}
    for key, value in context.items():
        if isinstance(value, Path):
            safe[key] = str(value)
        else:
            safe[key] = value
    return template.format(**safe)


def coerce_eval_payload(raw: object) -> dict[str, bool]:
    if isinstance(raw, dict):
        if "evals" in raw and isinstance(raw["evals"], dict):
            return {str(name): bool(value) for name, value in raw["evals"].items()}
        return {str(name): bool(value) for name, value in raw.items()}
    raise SystemExit("Evaluator output must be a JSON object or an object with an 'evals' map")


def run_shell(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, check=True)


def maybe_write_stdout(path: Path, stdout: str) -> None:
    if path.exists():
        return
    atomic_write(path, stdout)


def load_cached_evals(path: Path) -> dict[str, bool] | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    try:
        evals = coerce_eval_payload(payload)
    except SystemExit:
        return None
    return evals if evals else None


def parse_sample_indexes(raw: str | None, total: int) -> set[int] | None:
    if raw is None:
        return None
    indexes: set[int] = set()
    for part in raw.split(","):
        value = part.strip()
        if not value:
            continue
        if not value.isdigit():
            raise SystemExit(f"Invalid sample index: {value}")
        index = int(value)
        if index < 1 or index > total:
            raise SystemExit(f"Sample index out of range: {index}")
        indexes.add(index)
    if not indexes:
        raise SystemExit("--sample-indexes was provided but no valid indexes were found")
    return indexes


def merge_samples(existing: list[dict], updates: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for item in existing:
        sample_id = str(item.get("sample_id", "")).strip()
        if sample_id:
            merged[sample_id] = item
    for item in updates:
        sample_id = str(item.get("sample_id", "")).strip()
        if sample_id:
            merged[sample_id] = item
    def sort_key(item: dict) -> tuple[int, str]:
        sample_id = str(item.get("sample_id", ""))
        if sample_id.startswith("sample-"):
            suffix = sample_id.split("-", 1)[1]
            if suffix.isdigit():
                return (int(suffix), sample_id)
        return (10**9, sample_id)
    return sorted(merged.values(), key=sort_key)


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a per-sample generate/evaluate pipeline from an autoresearch run spec.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch run directory")
    parser.add_argument("--experiment-id", required=True, type=int, help="Experiment number")
    parser.add_argument("--candidate-file", default=None, help="Optional candidate file override")
    parser.add_argument("--generate-command", default=None, help="Shell command template to generate one sample output")
    parser.add_argument("--eval-command", default=None, help="Shell command template to evaluate one sample output")
    parser.add_argument("--results-output", default=None, help="Where to write the combined per-sample results JSON")
    parser.add_argument("--force-rerun", action="store_true", help="Ignore cached successful samples and rerun generation/eval")
    parser.add_argument("--sample-indexes", default=None, help="Optional comma-separated 1-based sample indexes to run, e.g. 1,3")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    run_spec = load_json(run_dir / "run-spec.json")
    results_payload = load_json(run_dir / "results.json")

    candidate_name = args.candidate_file or results_payload.get("candidate_file") or run_spec.get("candidate_file")
    if not candidate_name:
        raise SystemExit("Could not determine candidate file")
    candidate_file = Path(candidate_name).expanduser().resolve() if Path(str(candidate_name)).is_absolute() else run_dir / str(candidate_name)
    if not candidate_file.exists():
        raise SystemExit(f"Candidate file does not exist: {candidate_file}")

    generate_command = args.generate_command or run_spec.get("generate_command")
    eval_command = args.eval_command or run_spec.get("eval_command")
    if not generate_command:
        raise SystemExit("A generate command is required, either via --generate-command or run-spec.json")
    if not eval_command:
        raise SystemExit("An eval command is required, either via --eval-command or run-spec.json")

    test_inputs = run_spec.get("test_inputs", [])
    if not isinstance(test_inputs, list) or not test_inputs:
        raise SystemExit("run-spec.json must contain a non-empty test_inputs list")
    selected_indexes = parse_sample_indexes(args.sample_indexes, len(test_inputs))

    experiment_dir = run_dir / "outputs" / f"experiment-{args.experiment_id}"
    experiment_dir.mkdir(parents=True, exist_ok=True)

    samples = []
    resumed_samples = 0
    generated_samples = 0
    for index, prompt in enumerate(test_inputs, start=1):
        if selected_indexes is not None and index not in selected_indexes:
            continue
        sample_id = f"sample-{index}"
        sample_dir = experiment_dir / sample_id
        sample_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = sample_dir / "prompt.txt"
        output_file = sample_dir / "output.txt"
        eval_output_file = sample_dir / "evals.json"
        atomic_write(prompt_file, str(prompt).strip() + "\n")

        context = {
            "run_dir": run_dir,
            "experiment_id": args.experiment_id,
            "sample_id": sample_id,
            "sample_index": index,
            "candidate_file": candidate_file,
            "run_spec_json": run_dir / "run-spec.json",
            "prompt_file": prompt_file,
            "prompt_text": str(prompt),
            "prompt_text_json": json.dumps(str(prompt), ensure_ascii=False),
            "sample_dir": sample_dir,
            "output_file": output_file,
            "eval_output_file": eval_output_file,
        }

        cached_evals = None
        output_text = output_file.read_text(encoding="utf-8").strip() if output_file.exists() else ""
        if not args.force_rerun and output_text:
            cached_evals = load_cached_evals(eval_output_file)

        if cached_evals is not None:
            evals = cached_evals
            resumed_samples += 1
        else:
            generate_cp = run_shell(render_template(str(generate_command), context), run_dir)
            maybe_write_stdout(output_file, generate_cp.stdout)
            if not output_file.exists() or not output_file.read_text(encoding="utf-8").strip():
                raise SystemExit(f"Generate command did not produce non-empty output at {output_file}")

            if eval_output_file.exists():
                eval_output_file.unlink()
            eval_cp = run_shell(render_template(str(eval_command), context), run_dir)
            if not eval_output_file.exists():
                maybe_write_stdout(eval_output_file, eval_cp.stdout)
            if not eval_output_file.exists():
                raise SystemExit(f"Eval command did not create {eval_output_file} and produced no stdout")

            eval_payload = json.loads(eval_output_file.read_text(encoding="utf-8"))
            evals = coerce_eval_payload(eval_payload)
            generated_samples += 1

        samples.append(
            {
                "sample_id": sample_id,
                "prompt": str(prompt),
                "prompt_file": str(prompt_file),
                "output_file": str(output_file),
                "evals": evals,
            }
        )

    results_output = (
        Path(args.results_output).expanduser().resolve()
        if args.results_output
        else run_dir / "scorecards" / f"experiment-{args.experiment_id}-results.json"
    )
    results_output.parent.mkdir(parents=True, exist_ok=True)
    existing_payload = load_json(results_output)
    existing_samples = existing_payload.get("samples", []) if isinstance(existing_payload, dict) else []
    merged_samples = merge_samples(existing_samples if isinstance(existing_samples, list) else [], samples)
    payload = {"experiment_id": args.experiment_id, "samples": merged_samples}
    atomic_write(results_output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "results_output": str(results_output),
                "sample_count": len(merged_samples),
                "updated_samples": len(samples),
                "resumed_samples": resumed_samples,
                "generated_samples": generated_samples,
                "experiment_dir": str(experiment_dir),
                "candidate_file": str(candidate_file),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
