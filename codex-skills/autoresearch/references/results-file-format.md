# Per-sample results file format

`scripts/score_run.py` and `scripts/experiment_runner.py` expect a JSON file containing per-sample eval results.

Supported shapes:

## Shape A: plain list

```json
[
  {
    "sample_id": "p1",
    "evals": {
      "Sparse-input restraint": true,
      "Closure challenge": false
    }
  },
  {
    "sample_id": "p2",
    "evals": {
      "Sparse-input restraint": true,
      "Closure challenge": true
    }
  }
]
```

## Shape B: wrapped object

```json
{
  "samples": [
    {
      "sample_id": "p1",
      "evals": {
        "Sparse-input restraint": true,
        "Closure challenge": false
      }
    }
  ]
}
```

## Notes

- Every sample should contain an `evals` object.
- Every key in `evals` is the eval name.
- Every value in `evals` is a boolean pass/fail result.
- `score_run.py` computes:
  - total score
  - max score
  - pass rate
  - per-eval breakdown
- The aggregate score is simply the number of `true` values across all samples and evals.
