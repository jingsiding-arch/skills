#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    return json.loads(text) if text else {}


def next_experiment_id(run_dir: Path) -> int:
    results_path = run_dir / "results.json"
    payload = load_json(results_path)
    experiments = payload.get("experiments", [])
    if not experiments:
        return 0
    return max(int(item.get("id", -1)) for item in experiments) + 1


def parse_budget_cap(run_dir: Path) -> int | None:
    payload = load_json(run_dir / "run-spec.json")
    raw = str(payload.get("budget_cap", "")).strip().lower()
    if not raw or raw == "no cap":
        return None
    match = re.search(r"\d+", raw)
    return int(match.group(0)) if match else None


def format_template(value: str | None, **kwargs: object) -> str | None:
    if not value:
        return None
    return value.format(**kwargs)


def result_status(run_dir: Path, experiment_id: int) -> dict | None:
    payload = load_json(run_dir / "results.json")
    for item in payload.get("experiments", []):
        if int(item.get("id", -1)) == experiment_id:
            return item
    return None


def best_pass_rate(run_dir: Path) -> float | None:
    payload = load_json(run_dir / "results.json")
    values = [float(item.get("pass_rate", 0.0)) for item in payload.get("experiments", [])]
    return max(values) if values else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an autoresearch loop across baseline and follow-up experiments.")
    parser.add_argument("--run-dir", required=True, help="Path to autoresearch run directory")
    parser.add_argument("--max-new-experiments", type=int, default=3, help="How many new experiments to attempt in this invocation")
    parser.add_argument("--results-pattern", default=None, help="Pattern to locate per-experiment results JSON, e.g. /tmp/results-{experiment_id}.json")
    parser.add_argument("--sample-pattern", default=None, help="Pattern to locate per-experiment sample outputs, e.g. /tmp/outputs-{experiment_id}")
    parser.add_argument("--runner-command", default=None, help="Optional shell command template that should create the results file; placeholders: {run_dir} {experiment_id} {results_file} {sample_source} {candidate_file}")
    parser.add_argument("--generate-command", default=None, help="Optional shell command template for generating one sample output")
    parser.add_argument("--eval-command", default=None, help="Optional shell command template for evaluating one sample output")
    parser.add_argument("--target-pass-rate", type=float, default=95.0, help="Stop once the best kept pass rate reaches this threshold")
    parser.add_argument("--max-consecutive-nonimproving", type=int, default=3, help="Stop after this many consecutive non-improving non-baseline experiments")
    parser.add_argument("--keep-on-tie", action="store_true", help="Keep equal-scoring experiments")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).expanduser().resolve()
    budget_cap = parse_budget_cap(run_dir)
    experiment_id = next_experiment_id(run_dir)
    completed = 0
    consecutive_nonimproving = 0
    loop_summary = []

    auto_mutate_script = Path(__file__).with_name("auto_mutate.py")
    runner_script = Path(__file__).with_name("experiment_runner.py")
    execute_pipeline_script = Path(__file__).with_name("execute_target_pipeline.py")

    while completed < args.max_new_experiments:
        if budget_cap is not None and experiment_id >= budget_cap:
            break

        payload = load_json(run_dir / "results.json")
        candidate_name = str(payload.get("candidate_file", "candidate.md"))
        candidate_file = run_dir / candidate_name
        run_spec = load_json(run_dir / "run-spec.json")
        results_file = format_template(
            args.results_pattern,
            run_dir=run_dir,
            experiment_id=experiment_id,
            candidate_file=candidate_file,
        )
        sample_source = format_template(
            args.sample_pattern,
            run_dir=run_dir,
            experiment_id=experiment_id,
            candidate_file=candidate_file,
        )

        mutation_note = "baseline"
        description = "baseline"
        if experiment_id > 0:
            mutation_proc = subprocess.run(
                [sys.executable, str(auto_mutate_script), "--run-dir", str(run_dir), "--experiment-id", str(experiment_id), "--apply"],
                check=True,
                capture_output=True,
                text=True,
            )
            mutation_payload = json.loads(mutation_proc.stdout.strip())
            mutation_note = str(mutation_payload.get("mutation_note", f"auto mutation {experiment_id}"))
            description = f"auto mutation {experiment_id}: {mutation_note}"

        if args.runner_command:
            command = args.runner_command.format(
                run_dir=run_dir,
                experiment_id=experiment_id,
                results_file=results_file or "",
                sample_source=sample_source or "",
                candidate_file=candidate_file,
            )
            subprocess.run(command, shell=True, check=True)
        elif args.generate_command or args.eval_command or run_spec.get("generate_command") or run_spec.get("eval_command"):
            auto_results = run_dir / "scorecards" / f"experiment-{experiment_id}-results.json"
            pipeline_command = [
                sys.executable,
                str(execute_pipeline_script),
                "--run-dir",
                str(run_dir),
                "--experiment-id",
                str(experiment_id),
                "--results-output",
                str(auto_results),
            ]
            generate_command = args.generate_command or run_spec.get("generate_command")
            eval_command = args.eval_command or run_spec.get("eval_command")
            if generate_command:
                pipeline_command.extend(["--generate-command", str(generate_command)])
            if eval_command:
                pipeline_command.extend(["--eval-command", str(eval_command)])
            subprocess.run(pipeline_command, check=True)
            results_file = str(auto_results)
            sample_source = None

        if not results_file:
            raise SystemExit("run_experiment_loop.py needs either --results-pattern or --runner-command that writes a results file")
        results_path = Path(results_file).expanduser().resolve()
        if not results_path.exists():
            raise SystemExit(f"Expected results file does not exist: {results_path}")

        command = [
            sys.executable,
            str(runner_script),
            "--run-dir",
            str(run_dir),
            "--experiment-id",
            str(experiment_id),
            "--description",
            description,
            "--mutation-note",
            mutation_note,
            "--results-file",
            str(results_path),
            "--decision",
            "auto",
            "--run-status",
            "running",
        ]
        if args.keep_on_tie:
            command.append("--keep-on-tie")
        if sample_source:
            command.extend(["--sample-source", sample_source])
        subprocess.run(command, check=True)

        result = result_status(run_dir, experiment_id)
        if not result:
            raise SystemExit(f"Experiment {experiment_id} did not appear in results.json")
        loop_summary.append(result)

        if experiment_id > 0:
            best_before = max(
                (
                    float(item.get("pass_rate", 0.0))
                    for item in payload.get("experiments", [])
                    if item.get("status") in {"baseline", "keep"}
                ),
                default=None,
            )
            improved = best_before is None or float(result.get("pass_rate", 0.0)) > best_before or (
                args.keep_on_tie and float(result.get("pass_rate", 0.0)) == best_before and result.get("status") == "keep"
            )
            consecutive_nonimproving = 0 if improved else consecutive_nonimproving + 1

        current_best = best_pass_rate(run_dir)
        completed += 1
        experiment_id += 1

        if current_best is not None and current_best >= args.target_pass_rate:
            break
        if consecutive_nonimproving >= args.max_consecutive_nonimproving:
            break

    final_payload = load_json(run_dir / "results.json")
    if final_payload:
        final_payload["status"] = "complete"
        Path(run_dir / "results.json").write_text(json.dumps(final_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "completed_experiments": completed,
                "loop_summary": loop_summary,
                "best_pass_rate": best_pass_rate(run_dir),
                "next_experiment_id": experiment_id,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
