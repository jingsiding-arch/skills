---
name: autoresearch
description: Autonomously benchmark and improve an existing Codex skill by running it repeatedly against multiple test prompts, scoring outputs with binary evals, and iterating on the skill instructions while preserving the original. Use when Codex needs to optimize a SKILL.md, stabilize a flaky skill, run evals on a skill, compare prompt-level mutations, or keep a research log of which skill edits helped.
---

# Autoresearch

Use this skill to optimize another skill through repeated measurement instead of intuition.

Treat the target skill as the system under test. Run it on several representative prompts, score each output with binary evals, make one focused mutation, and keep only changes that measurably help.

## Required run spec before starting

Stop before running any experiment.

Do not create a baseline, initialize a run directory, or mutate any skill until the run spec below is collected and frozen.

Use `references/run-spec-template.md` as the default intake sheet.

If you want the system to run each sample for you, also record:

- a generate command
- an eval command

See `references/pipeline-command-placeholders.md`.

For a ready-made example, see `references/module-prd-writer-adapter.md`.

Do not run experiments until all of these are fixed:

1. **Target skill path**: exact path to the target `SKILL.md`
2. **Test inputs**: 3-5 prompts or scenarios that cover different use cases
3. **Eval criteria**: 3-6 binary yes/no checks
4. **Runs per experiment**: default `5`
5. **Run interval**: how often to cycle experiments; default `every 2 minutes`
6. **Budget cap**: optional max number of experiment cycles before stopping

If any field is missing, ask the user for it before continuing.

If the user gives vague evals, read `references/eval-guide.md` and rewrite them into binary checks, then explicitly confirm the rewritten evals as the run spec.

If the user does not care about run interval or budget cap, record defaults explicitly instead of leaving them implicit.

## Run-spec freeze rule

Before experimentation, restate the final run spec in one compact block and treat it as frozen for the rest of the run:

- target skill
- test inputs
- eval criteria
- runs per experiment
- run interval
- budget cap

Do not silently change these mid-run.

If the user changes any of them later, record that as a new run or an explicit rerun condition instead of mixing incompatible results into one experiment series.

## Core rules

- Never modify the original target `SKILL.md`
- Work on a copied candidate file only
- Never start experiments with missing run-spec fields
- Change one thing at a time
- Reuse the same test inputs and evals across experiments
- Keep a full log of every experiment, including discarded ones
- Prefer shorter, sharper mutations over sprawling rewrites
- Stop if the evals are obviously bad or are being gamed

## Workflow

### 1. Read the target skill first

Only do this after the run spec is collected.

Before making changes:

1. Read the full target `SKILL.md`
2. Read only the reference files it actually uses
3. Identify:
   - its core job
   - the expected output format
   - likely failure modes
   - any existing guardrails or anti-patterns

Do not mutate a skill you do not understand.

### 2. Build the eval suite

Only use the user-approved eval criteria for the active run.

Represent each eval in this format:

```text
EVAL [N]: [Short name]
Question: [Yes/no question]
Pass: [Specific pass condition]
Fail: [Specific fail condition]
```

Guidance:

- Use only binary checks
- Avoid overlapping evals
- Avoid style-only evals that can be gamed
- Prefer checks tied to the user's real quality bar
- If you rewrote vague evals, show the rewritten set before proceeding

### 2.5 Confirm the run spec

Before initializing files, output a compact run-spec summary such as:

```text
Run spec
- Target skill: ...
- Test inputs: ...
- Evals: ...
- Runs per experiment: ...
- Run interval: ...
- Budget cap: ...
```

Then proceed only if the run spec is complete.

### 3. Initialize the experiment workspace

Create a sibling working directory named:

```text
autoresearch-[skill-name]/
```

Use `scripts/init_run.py` to create:

- `run-spec.md`
- `run-spec.json`
- `dashboard.html`
- `results.json`
- `results.tsv`
- `changelog.md`
- `mutations.md`
- `SKILL.md.baseline`
- `[candidate-name].md`
- `outputs/`
- `scorecards/`
- `candidate-history/`

Recommended command:

```bash
python3 scripts/init_run.py \
  --skill /absolute/path/to/target/SKILL.md \
  --candidate-name target-skill-optimized \
  --test-input-file /path/to/test-inputs.txt \
  --eval-file /path/to/evals.md \
  --generate-command "python3 my_generator.py --candidate-file {candidate_file} --prompt-file {prompt_file} --output-file {output_file}" \
  --eval-command "python3 my_evaluator.py --run-spec {run_spec_json} --prompt-file {prompt_file} --output-file {output_file} --eval-output {eval_output_file}"
```

Use `--output-dir` when the run directory should live somewhere else.

If you already know the run spec values, pass them into `init_run.py` so the run directory is born with a frozen `run-spec.md`.

### 3.5 Prepare a mutation

When you are ready to test a new prompt mutation, use `scripts/mutate_candidate.py` to snapshot the current candidate and either:

- copy in a fully edited candidate file, or
- apply a simple find/replace mutation

Example:

```bash
python3 scripts/mutate_candidate.py \
  --run-dir /path/to/autoresearch-skill \
  --experiment-id 1 \
  --mutation-note "move anti-pattern section higher" \
  --source-file /path/to/edited-candidate.md
```

This creates before/working snapshots in `candidate-history/` and appends a row to `mutations.md`.

### 3.6 Auto-propose the next mutation

When you want the system to suggest the next change by itself, use `scripts/auto_mutate.py`.

It reads:

- the latest scorecard
- the weakest evals
- the frozen run spec

Then it writes:

- `auto-mutations/experiment-[N].md`
- `auto-mutations/experiment-[N].json`

If you pass `--apply`, it also applies the proposed reinforcement to the current candidate and snapshots the change.

Example:

```bash
python3 scripts/auto_mutate.py \
  --run-dir /path/to/autoresearch-skill \
  --experiment-id 2 \
  --apply
```

### 4. Establish the baseline

Experiment `0` is always the untouched copy.

1. Run the target skill with the agreed test inputs
2. Score every output against every eval
3. Record experiment `0` as `baseline`
4. Confirm whether the baseline is already high enough that more work may not be worth it

Use `scripts/archive_samples.py` to copy raw outputs into `outputs/experiment-[N]/`.

Use `references/results-file-format.md` for the expected per-sample scoring JSON shape.

Use `scripts/score_run.py` when you have per-sample eval results and want to auto-aggregate:

```bash
python3 scripts/score_run.py \
  --run-dir /path/to/autoresearch-skill \
  --experiment-id 0 \
  --status baseline \
  --description "original skill baseline" \
  --results-file /path/to/baseline-results.json
```

Use `scripts/log_experiment.py` only when you already know the aggregate score and just want to write the experiment summary directly.

Use `scripts/execute_target_pipeline.py` when you already know how to run one sample and how to evaluate one sample, and you want the system to generate the whole per-experiment results file automatically.

Example:

```bash
python3 scripts/execute_target_pipeline.py \
  --run-dir /path/to/autoresearch-skill \
  --experiment-id 0
```

Use `scripts/experiment_runner.py` when you want one higher-level command that:

- archives raw outputs
- computes the score
- auto-decides keep/discard
- updates `results.tsv` and `results.json`
- appends to `changelog.md`
- updates `mutations.md`
- keeps or reverts the candidate file automatically

Example:

```bash
python3 scripts/experiment_runner.py \
  --run-dir /path/to/autoresearch-skill \
  --experiment-id 1 \
  --description "tightened draft-mode instructions" \
  --results-file /path/to/experiment-1-results.json \
  --sample-source /path/to/output-dir \
  --decision auto
```

Use `scripts/run_experiment_loop.py` when you want the system to keep going for several rounds instead of one round at a time.

The loop runner can:

- run the baseline if needed
- auto-propose the next mutation
- auto-run every sample if generate/eval commands are available
- score each round
- decide keep or discard
- stop after enough non-improving rounds or once the score is high enough

### 5. Run the mutation loop

For each new experiment:

1. Inspect failing outputs
2. Form one hypothesis about why they failed
3. Make one targeted change to the candidate file
4. Re-run the same test inputs
5. Score the outputs
6. Decide:
   - improved: keep
   - same: discard unless the skill became materially simpler
   - worse: discard
7. Log the experiment and what changed

Honor the frozen run spec throughout the loop:

- keep the same test inputs
- keep the same evals
- keep the same scoring logic
- respect the recorded run interval and budget cap

If you need to change the eval suite because it is bad, stop the current run and start a new run spec instead of mutating the benchmark in place.

Good mutations:

- clarify an ambiguous instruction
- move an important rule earlier
- add a concrete anti-pattern
- tighten output format instructions
- add one short example
- delete a harmful or redundant rule

Bad mutations:

- rewriting the whole skill at once
- adding many new rules with no diagnosis
- optimizing to one test prompt
- making the skill longer without a clear failure to fix

### 6. Keep the changelog useful

Every experiment entry should capture:

- score and pass rate
- keep or discard
- exact change made
- why it was expected to help
- what improved or regressed
- what still fails

Future agents should be able to continue from the log without re-deriving your reasoning.

### 7. Deliver the results

At the end, present:

1. baseline score to final score
2. total experiments run
3. keep rate
4. top changes that helped
5. remaining failure patterns
6. path to the improved candidate file
7. path to `results.tsv` and `changelog.md`

Do not overwrite the original skill unless the user explicitly asks for that final merge.

## Bundled scripts

### `scripts/init_run.py`

Initialize a fresh experiment directory and seed:

- frozen run-spec files
- dashboard data
- TSV log
- changelog
- baseline copy
- candidate copy
- artifact folders for outputs, scorecards, and candidate history

### `scripts/archive_samples.py`

Copy raw sample outputs into:

```text
outputs/experiment-[N]/
```

Use this to preserve the exact artifacts that were scored.

### `scripts/score_run.py`

Convert per-sample eval results into:

- aggregate score
- per-eval breakdown
- `scorecards/experiment-[N].json`
- updated `results.tsv`
- updated `results.json`

### `scripts/execute_target_pipeline.py`

Run the execution bridge for one experiment:

- read test inputs from the frozen run spec
- generate one output per sample
- evaluate one output per sample
- combine those sample-level evals into a single results JSON file

### `scripts/log_experiment.py`

Append or update one experiment record and regenerate `results.json` for the dashboard.

This is the lower-level logger. Prefer `score_run.py` when you have raw per-sample eval results.

### `scripts/mutate_candidate.py`

Snapshot the current candidate before a mutation and prepare the working candidate for the next experiment.

This is useful when the actual content edit is done outside the run directory but you still want clean mutation bookkeeping.

### `scripts/auto_mutate.py`

Suggest the next mutation automatically based on the weakest evals from the latest scorecard.

This is what makes the system start feeling less manual.

### `scripts/experiment_runner.py`

Run one higher-level experiment lifecycle:

- archive outputs
- score the run
- decide baseline / keep / discard
- update dashboard data
- snapshot or revert the candidate
- append to changelog and mutation log

### `scripts/run_experiment_loop.py`

Run several experiments in sequence.

This is the closest thing to a "press go and let it keep trying" loop in the current system.

It still needs a per-experiment results JSON file, either by:

- precomputing files like `results-0.json`, `results-1.json`, `results-2.json`, or
- passing a `--runner-command` that creates those files during the loop

If the run spec already contains a generate command and an eval command, the loop can create those result files by itself.

## Output contract

The run directory should contain:

```text
autoresearch-[skill-name]/
├── run-spec.md
├── run-spec.json
├── dashboard.html
├── results.json
├── results.tsv
├── changelog.md
├── mutations.md
├── SKILL.md.baseline
├── [candidate-name].md
├── auto-mutations/
├── outputs/
├── scorecards/
└── candidate-history/
```

`results.tsv` should use these columns:

```text
experiment	score	max_score	pass_rate	status	description
```

The run notes should also preserve the run spec used for that experiment series, either in the changelog header or in a separate run-spec note.

Raw outputs and scorecards should be preserved so another agent can audit why a score changed instead of trusting the aggregate summary alone.

The mutation log should preserve which candidate version was under evaluation for each experiment.

## Success criteria

A good autoresearch run:

1. collected and froze the full run spec before editing
2. measured a baseline before editing
3. used binary evals only
4. changed one variable at a time
5. logged every experiment
6. improved the measured score or simplified the skill without regression
7. avoided overfitting to one prompt

If the skill appears to improve while real output quality does not, assume the evals are weak and rewrite the eval suite before continuing.
