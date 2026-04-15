# Autoresearch run-spec template

Use this before any experiments begin.

Do not start a baseline or mutate the target skill until every field below is filled.

## Required fields

### 1. Target skill

- Exact path to target `SKILL.md`:
- Skill name:

### 2. Test inputs

Provide 3-5 prompts or scenarios that cover different use cases:

1.
2.
3.
4.
5.

### 3. Eval criteria

Provide 3-6 binary yes/no checks.

```text
EVAL 1: [Short name]
Question: [Yes/no question]
Pass: [Specific pass condition]
Fail: [Specific fail condition]
```

Repeat for each eval.

If the user's wording is vague, rewrite it into binary form and confirm that rewritten version as the active eval suite.

### 4. Runs per experiment

- Default: `5`
- Chosen value:

### 5. Run interval

- Default: `every 2 minutes`
- Chosen value:

### 6. Budget cap

- Optional maximum number of experiment cycles:
- If none, explicitly write `no cap`

## Optional execution bridge

If you want the system to run each sample for you instead of waiting for a hand-made results file, also record:

- Generate command:
- Eval command:

The generate command should create one sample output.

The eval command should judge one sample output and write an eval JSON object.

See `references/pipeline-command-placeholders.md` for supported placeholders.

## Freeze block

Before experimentation, restate the final run spec in a compact block:

```text
Run spec
- Target skill: ...
- Test inputs: ...
- Evals: ...
- Runs per experiment: ...
- Run interval: ...
- Budget cap: ...
```

Treat that block as frozen for the active run.

If the user later changes any field, start a new run or mark it as a rerun with a new spec.
