# Module PRD writer adapter

This adapter connects `autoresearch` to `module-prd-writer`.

## What it adds

- a fixed PRD test set
- a fixed PRD eval set
- a generator that calls `codex exec` with the candidate skill and supporting references
- a deterministic evaluator for the PRD-specific binary checks

## Files

- `assets/module-prd-writer-test-inputs.txt`
- `assets/module-prd-writer-evals.md`
- `scripts/generate_via_codex_skill.py`
- `scripts/eval_module_prd_writer.py`
- `scripts/init_module_prd_writer_run.py`

## One-command setup

```bash
python3 scripts/init_module_prd_writer_run.py
```

This creates a ready-to-run autoresearch workspace with:

- frozen test inputs
- frozen evals
- generate command
- eval command

## After setup

Run the loop with:

```bash
python3 scripts/run_experiment_loop.py \
  --run-dir /path/to/module-prd-writer-live \
  --max-new-experiments 3
```

If network access for `codex exec` is blocked in the current environment, the adapter is still fully configured; the actual generation step just needs network-enabled execution.
