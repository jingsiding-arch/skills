#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a ready-to-run autoresearch workspace for module-prd-writer.")
    parser.add_argument("--run-dir", default="/Users/homg/Documents/Codex/skills/autoresearch-runs/module-prd-writer-live")
    parser.add_argument("--candidate-name", default="module-prd-writer-candidate")
    parser.add_argument("--target-skill", default="/Users/homg/.codex/skills/module-prd-writer/SKILL.md")
    parser.add_argument("--model", default=None, help="Optional codex model override for generation")
    parser.add_argument("--sample-timeout-seconds", type=int, default=90, help="Timeout for one generated sample")
    args = parser.parse_args()

    skill_root = str(Path(args.target_skill).expanduser().resolve().parent)
    this_dir = Path(__file__).resolve().parent
    init_run = this_dir / "init_run.py"
    generate_script = this_dir / "generate_via_codex_skill.py"
    eval_script = this_dir / "eval_module_prd_writer.py"
    test_inputs = this_dir.parent / "assets" / "module-prd-writer-test-inputs.txt"
    evals = this_dir.parent / "assets" / "module-prd-writer-evals.md"

    generate_command = (
        f"python3 {generate_script} --candidate-file {{candidate_file}} --prompt-file {{prompt_file}} "
        f"--output-file {{output_file}} --skill-root {skill_root} --timeout-seconds {args.sample_timeout_seconds}"
    )
    if args.model:
        generate_command += f" --model {args.model}"
    eval_command = (
        f"python3 {eval_script} --run-spec {{run_spec_json}} --prompt-file {{prompt_file}} "
        f"--output-file {{output_file}} --eval-output {{eval_output_file}}"
    )

    command = [
        sys.executable,
        str(init_run),
        "--skill",
        str(Path(args.target_skill).expanduser().resolve()),
        "--candidate-name",
        args.candidate_name,
        "--output-dir",
        str(Path(args.run_dir).expanduser().resolve()),
        "--test-input-file",
        str(test_inputs),
        "--eval-file",
        str(evals),
        "--runs-per-experiment",
        "5",
        "--run-interval",
        "every 2 minutes",
        "--budget-cap",
        "10",
        "--generate-command",
        generate_command,
        "--eval-command",
        eval_command,
    ]
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
