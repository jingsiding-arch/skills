#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path


RESULTS_HEADER = "experiment\tscore\tmax_score\tpass_rate\tstatus\tdescription\n"


def atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "candidate"


def load_test_inputs(path: Path | None) -> list[str]:
    if not path:
        return []
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, list):
            raise SystemExit("test-input file must be a JSON array or a plain-text list")
        return [str(item).strip() for item in data if str(item).strip()]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    normalized: list[str] = []
    for line in lines:
        normalized.append(re.sub(r"^\d+\.\s*", "", line))
    return normalized


def parse_eval_text(text: str) -> list[dict]:
    blocks = re.split(r"\n(?=EVAL\s+\d+\s*:)", text.strip(), flags=re.IGNORECASE)
    normalized: list[dict] = []
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        match = re.match(r"EVAL\s+\d+\s*:\s*(.+)$", lines[0], flags=re.IGNORECASE)
        name = match.group(1).strip() if match else ""
        question = ""
        passed = ""
        failed = ""
        for line in lines[1:]:
            if re.match(r"Question\s*:", line, flags=re.IGNORECASE):
                question = re.sub(r"^Question\s*:\s*", "", line, flags=re.IGNORECASE)
            elif re.match(r"Pass\s*:", line, flags=re.IGNORECASE):
                passed = re.sub(r"^Pass\s*:\s*", "", line, flags=re.IGNORECASE)
            elif re.match(r"Fail\s*:", line, flags=re.IGNORECASE):
                failed = re.sub(r"^Fail\s*:\s*", "", line, flags=re.IGNORECASE)
        normalized.append({"name": name, "question": question, "pass": passed, "fail": failed})
    return normalized


def load_eval_block(path: Path | None) -> tuple[list[dict], str]:
    if not path:
        return [], ""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return [], ""
    if path.suffix.lower() == ".json":
        data = json.loads(text)
        if not isinstance(data, list):
            raise SystemExit("eval file must be a JSON array or markdown/plain text")
        normalized = []
        blocks = []
        for item in data:
            if not isinstance(item, dict):
                raise SystemExit("each eval JSON entry must be an object")
            normalized_item = {
                "name": str(item.get("name", "")).strip(),
                "question": str(item.get("question", "")).strip(),
                "pass": str(item.get("pass", "")).strip(),
                "fail": str(item.get("fail", "")).strip(),
            }
            normalized.append(normalized_item)
            blocks.append(
                "\n".join(
                    [
                        f"EVAL {len(normalized)}: {normalized_item['name'] or '[Short name]'}",
                        f"Question: {normalized_item['question'] or '[Yes/no question]'}",
                        f"Pass: {normalized_item['pass'] or '[Specific pass condition]'}",
                        f"Fail: {normalized_item['fail'] or '[Specific fail condition]'}",
                    ]
                )
            )
        return normalized, "\n\n".join(blocks)
    return parse_eval_text(text), text


def build_dashboard_html(skill_name: str) -> str:
    title = html.escape(f"Autoresearch Dashboard · {skill_name}")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --bg: #f7f8fc;
      --panel: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --blue: #91b4ff;
      --blue-strong: #4f7cff;
      --border: #e5e7eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, system-ui, sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    p {{ color: var(--muted); }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; margin: 24px 0; }}
    .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 16px; padding: 16px; box-shadow: 0 8px 32px rgba(31, 41, 55, 0.05); }}
    .k {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .v {{ font-size: 26px; font-weight: 700; margin-top: 6px; }}
    .stack {{ display: grid; gap: 16px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 12px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    th {{ color: var(--muted); font-weight: 600; }}
    .tag {{ display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }}
    .baseline {{ background: #dbeafe; color: #1d4ed8; }}
    .keep {{ background: #dcfce7; color: #166534; }}
    .discard {{ background: #fee2e2; color: #b91c1c; }}
    .idle {{ background: #ede9fe; color: #6d28d9; }}
    .bars {{ display: grid; gap: 12px; }}
    .bar-row {{ display: grid; gap: 6px; }}
    .bar {{ width: 100%; background: #eef2ff; border-radius: 999px; overflow: hidden; height: 12px; }}
    .fill {{ height: 12px; background: linear-gradient(90deg, var(--blue), var(--blue-strong)); }}
    @media (max-width: 860px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    @media (max-width: 580px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{html.escape(skill_name)} autoresearch</h1>
    <p id="statusLine">Loading…</p>
    <div class="grid">
      <div class="card"><div class="k">Current status</div><div class="v" id="statusValue">—</div></div>
      <div class="card"><div class="k">Current experiment</div><div class="v" id="currentExperiment">—</div></div>
      <div class="card"><div class="k">Baseline</div><div class="v" id="baselineScore">—</div></div>
      <div class="card"><div class="k">Best score</div><div class="v" id="bestScore">—</div></div>
    </div>
    <div class="stack">
      <div class="card"><canvas id="scoreChart" height="110"></canvas></div>
      <div class="card">
        <h2>Experiments</h2>
        <table>
          <thead><tr><th>#</th><th>Score</th><th>Pass rate</th><th>Status</th><th>Description</th></tr></thead>
          <tbody id="experimentsBody"></tbody>
        </table>
      </div>
      <div class="card">
        <h2>Per-eval breakdown</h2>
        <div class="bars" id="evalBars"></div>
      </div>
    </div>
  </div>
  <script>
    let chart;
    function tagClass(status) {{
      if (status === "baseline") return "tag baseline";
      if (status === "keep") return "tag keep";
      if (status === "discard") return "tag discard";
      return "tag idle";
    }}
    function render(data) {{
      document.getElementById("statusLine").textContent =
        data.status === "running" ? `Running experiment ${{data.current_experiment}}…`
        : data.status === "complete" ? "Run complete." : "Idle.";
      document.getElementById("statusValue").textContent = data.status || "idle";
      document.getElementById("currentExperiment").textContent = data.current_experiment ?? "—";
      document.getElementById("baselineScore").textContent = data.baseline_score == null ? "—" : `${{data.baseline_score.toFixed(1)}}%`;
      document.getElementById("bestScore").textContent = data.best_score == null ? "—" : `${{data.best_score.toFixed(1)}}%`;
      const labels = data.experiments.map(item => `#${{item.id}}`);
      const values = data.experiments.map(item => item.pass_rate);
      const colors = data.experiments.map(item => item.status === "baseline" ? "#4f7cff" : item.status === "keep" ? "#34d399" : "#f87171");
      if (!chart) {{
        chart = new Chart(document.getElementById("scoreChart"), {{
          type: "line",
          data: {{ labels, datasets: [{{ label: "Pass rate %", data: values, borderColor: "#4f7cff", pointBackgroundColor: colors, pointRadius: 5, tension: 0.25 }}] }},
          options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true, suggestedMax: 100 }} }} }}
        }});
      }} else {{
        chart.data.labels = labels;
        chart.data.datasets[0].data = values;
        chart.data.datasets[0].pointBackgroundColor = colors;
        chart.update();
      }}
      document.getElementById("experimentsBody").innerHTML = data.experiments.map(item => `
        <tr>
          <td>${{item.id}}</td>
          <td>${{item.score}} / ${{item.max_score}}</td>
          <td>${{item.pass_rate.toFixed(1)}}%</td>
          <td><span class="${{tagClass(item.status)}}">${{item.status}}</span></td>
          <td>${{item.description || ""}}</td>
        </tr>`).join("");
      document.getElementById("evalBars").innerHTML = (data.eval_breakdown || []).map(item => {{
        const pct = item.total ? (item.pass_count / item.total) * 100 : 0;
        return `<div class="bar-row"><div><strong>${{item.name}}</strong> · ${{item.pass_count}} / ${{item.total}} (${{pct.toFixed(1)}}%)</div><div class="bar"><div class="fill" style="width:${{pct}}%"></div></div></div>`;
      }}).join("") || "<p>No eval breakdown yet.</p>";
    }}
    async function load() {{
      try {{
        const response = await fetch("./results.json?ts=" + Date.now());
        render(await response.json());
      }} catch (error) {{
        document.getElementById("statusLine").textContent = "Failed to load results.json";
      }}
    }}
    load();
    setInterval(load, 10000);
  </script>
</body>
</html>
"""


def build_run_spec_markdown(
    skill_path: Path,
    skill_name: str,
    test_inputs: list[str],
    evals_block: str,
    runs_per_experiment: int | None,
    run_interval: str | None,
    budget_cap: str | None,
    generate_command: str | None,
    eval_command: str | None,
) -> str:
    test_input_lines = "\n".join(f"{idx}. {item}" for idx, item in enumerate(test_inputs, start=1)) if test_inputs else "1.\n2.\n3."
    eval_block = evals_block or (
        "EVAL 1: [Short name]\n"
        "Question: [Yes/no question]\n"
        "Pass: [Specific pass condition]\n"
        "Fail: [Specific fail condition]"
    )
    return (
        "# Autoresearch run spec\n\n"
        "## Frozen run spec\n\n"
        f"- Target skill: `{skill_path}`\n"
        f"- Skill name: `{skill_name}`\n"
        f"- Runs per experiment: `{runs_per_experiment if runs_per_experiment is not None else 5}`\n"
        f"- Run interval: `{run_interval or 'every 2 minutes'}`\n"
        f"- Budget cap: `{budget_cap or 'no cap'}`\n\n"
        "## Test inputs\n\n"
        f"{test_input_lines}\n\n"
        "## Eval criteria\n\n"
        "```text\n"
        f"{eval_block}\n"
        "```\n"
        "\n## Optional execution commands\n\n"
        f"- Generate command: `{generate_command or 'not set'}`\n"
        f"- Eval command: `{eval_command or 'not set'}`\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize an autoresearch run directory.")
    parser.add_argument("--skill", required=True, help="Absolute path to the target SKILL.md")
    parser.add_argument("--candidate-name", default=None, help="Base name for the candidate skill copy")
    parser.add_argument("--output-dir", default=None, help="Directory to create. Defaults to a sibling autoresearch-<skill-name> directory.")
    parser.add_argument("--test-input-file", default=None, help="Optional path to a JSON array or plain-text list of test prompts")
    parser.add_argument("--eval-file", default=None, help="Optional path to eval markdown or JSON array")
    parser.add_argument("--runs-per-experiment", type=int, default=None, help="Optional frozen runs-per-experiment value")
    parser.add_argument("--run-interval", default=None, help="Optional run interval label")
    parser.add_argument("--budget-cap", default=None, help="Optional budget cap label")
    parser.add_argument("--generate-command", default=None, help="Optional shell command template for generating one sample output")
    parser.add_argument("--eval-command", default=None, help="Optional shell command template for evaluating one sample output")
    args = parser.parse_args()

    skill_path = Path(args.skill).expanduser().resolve()
    if not skill_path.exists():
        raise SystemExit(f"Target skill does not exist: {skill_path}")
    if skill_path.name != "SKILL.md":
        raise SystemExit("Target path must point to a SKILL.md file")

    skill_name = skill_path.parent.name
    candidate_name = slugify(args.candidate_name or f"{skill_name}-optimized")
    run_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else skill_path.parent / f"autoresearch-{skill_name}"
    run_dir.mkdir(parents=True, exist_ok=True)

    outputs_dir = run_dir / "outputs"
    scorecards_dir = run_dir / "scorecards"
    candidates_dir = run_dir / "candidate-history"
    auto_mutations_dir = run_dir / "auto-mutations"
    for directory in (outputs_dir, scorecards_dir, candidates_dir, auto_mutations_dir):
        directory.mkdir(parents=True, exist_ok=True)

    candidate_file = run_dir / f"{candidate_name}.md"
    baseline_file = run_dir / "SKILL.md.baseline"
    run_spec_md = run_dir / "run-spec.md"
    run_spec_json = run_dir / "run-spec.json"
    results_tsv = run_dir / "results.tsv"
    results_json = run_dir / "results.json"
    changelog = run_dir / "changelog.md"
    mutations_md = run_dir / "mutations.md"
    dashboard = run_dir / "dashboard.html"

    shutil.copy2(skill_path, candidate_file)
    shutil.copy2(skill_path, baseline_file)
    shutil.copy2(skill_path, candidates_dir / "experiment-0-baseline.md")
    shutil.copy2(skill_path, candidates_dir / "current-candidate.md")

    test_inputs = load_test_inputs(Path(args.test_input_file).expanduser().resolve()) if args.test_input_file else []
    evals_structured, eval_block = load_eval_block(Path(args.eval_file).expanduser().resolve()) if args.eval_file else ([], "")

    run_spec_payload = {
        "target_skill": str(skill_path),
        "skill_name": skill_name,
        "test_inputs": test_inputs,
        "evals": evals_structured,
        "eval_block": eval_block,
        "runs_per_experiment": args.runs_per_experiment if args.runs_per_experiment is not None else 5,
        "run_interval": args.run_interval or "every 2 minutes",
        "budget_cap": args.budget_cap or "no cap",
        "generate_command": args.generate_command,
        "eval_command": args.eval_command,
        "candidate_file": candidate_file.name,
        "baseline_file": baseline_file.name,
    }
    atomic_write(run_spec_json, json.dumps(run_spec_payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write(
        run_spec_md,
        build_run_spec_markdown(
            skill_path=skill_path,
            skill_name=skill_name,
            test_inputs=test_inputs,
            evals_block=eval_block,
            runs_per_experiment=args.runs_per_experiment,
            run_interval=args.run_interval,
            budget_cap=args.budget_cap,
            generate_command=args.generate_command,
            eval_command=args.eval_command,
        ),
    )

    if not results_tsv.exists():
        atomic_write(results_tsv, RESULTS_HEADER)

    if not changelog.exists():
        atomic_write(
            changelog,
            "# Autoresearch changelog\n\n"
            f"- Target skill: `{skill_path}`\n"
            f"- Candidate file: `{candidate_file.name}`\n"
            f"- Run spec: `{run_spec_md.name}`\n\n",
        )

    if not mutations_md.exists():
        atomic_write(
            mutations_md,
            "# Mutation log\n\n"
            "| Experiment | Status | Mutation | Candidate snapshot |\n"
            "| --- | --- | --- | --- |\n",
        )

    payload = {
        "skill_name": skill_name,
        "status": "idle",
        "current_experiment": 0,
        "baseline_score": None,
        "best_score": None,
        "experiments": [],
        "eval_breakdown": [],
        "candidate_file": candidate_file.name,
        "baseline_file": baseline_file.name,
        "run_spec_file": run_spec_md.name,
        "run_spec": run_spec_payload,
    }
    atomic_write(results_json, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write(dashboard, build_dashboard_html(skill_name))

    summary = {
        "run_dir": str(run_dir),
        "candidate_file": str(candidate_file),
        "baseline_file": str(baseline_file),
        "run_spec_md": str(run_spec_md),
        "run_spec_json": str(run_spec_json),
        "outputs_dir": str(outputs_dir),
        "scorecards_dir": str(scorecards_dir),
        "candidates_dir": str(candidates_dir),
        "auto_mutations_dir": str(auto_mutations_dir),
        "results_tsv": str(results_tsv),
        "results_json": str(results_json),
        "dashboard_html": str(dashboard),
        "changelog_md": str(changelog),
        "mutations_md": str(mutations_md),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
