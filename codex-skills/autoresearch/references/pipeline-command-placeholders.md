# Pipeline command placeholders

`scripts/execute_target_pipeline.py` and `scripts/run_experiment_loop.py` support shell command templates.

These templates can use the placeholders below:

- `{run_dir}`
- `{experiment_id}`
- `{sample_id}`
- `{sample_index}`
- `{candidate_file}`
- `{run_spec_json}`
- `{sample_dir}`
- `{prompt_file}`
- `{prompt_text}`
- `{prompt_text_json}`
- `{output_file}`
- `{eval_output_file}`

## Recommended pattern

Prefer file-based placeholders over raw text placeholders.

Most robust:

- read the prompt from `{prompt_file}`
- write the model output to `{output_file}`
- write the per-sample eval JSON to `{eval_output_file}`

## Generate command example

```bash
python3 my_generator.py \
  --candidate-file {candidate_file} \
  --prompt-file {prompt_file} \
  --output-file {output_file}
```

## Eval command example

```bash
python3 my_evaluator.py \
  --run-spec {run_spec_json} \
  --prompt-file {prompt_file} \
  --output-file {output_file} \
  --eval-output {eval_output_file}
```

## Expected evaluator output

The evaluator should produce a JSON object like:

```json
{
  "Sparse-input restraint": true,
  "Closure challenge": false
}
```

or:

```json
{
  "evals": {
    "Sparse-input restraint": true,
    "Closure challenge": false
  }
}
```
