# Eval Guide

Write eval criteria that improve the skill instead of flattering it.

## Golden rule

Every eval must be binary: yes or no.

Avoid:

- 1-5 or 1-10 scales
- vibe checks
- vague adjectives like "good" or "professional"

Binary evals produce a cleaner signal across repeated runs.

## Good vs bad evals

### Writing skills

Bad:

- "Is the writing good?"
- "Does it sound human?"
- "Rate the persuasion from 1-10"

Good:

- "Does the output avoid every phrase in the banned list?"
- "Does the opening contain a concrete detail rather than a generic setup?"
- "Does the output end with a specific next action?"

### Visual or UI skills

Bad:

- "Does it look nice?"
- "Is the layout good?"
- "Rate the visual quality"

Good:

- "Is all visible text legible with no overlap or truncation?"
- "Does the palette avoid neon or overly saturated colors?"
- "Does the layout follow a clear directional flow?"

### Coding skills

Bad:

- "Is the code clean?"
- "Does it follow best practices?"

Good:

- "Does the code run without errors?"
- "Does the output contain zero TODO or placeholder comments?"
- "Does every external call include error handling?"

### Document skills

Bad:

- "Is it comprehensive?"
- "Does it meet the client's needs?"

Good:

- "Does it contain every required section?"
- "Is each claim supported by a number, date, or cited source when required?"
- "Does the summary stay within the requested length limit?"

## Three quick tests for every eval

Before locking an eval, ask:

1. Would two agents score the same output the same way?
2. Could the skill game this eval without actually improving?
3. Does this eval measure something the user truly cares about?

If any answer is bad, rewrite the eval.

## Template

```text
EVAL [N]: [Short name]
Question: [Yes/no question]
Pass: [One specific sentence]
Fail: [One specific sentence]
```
