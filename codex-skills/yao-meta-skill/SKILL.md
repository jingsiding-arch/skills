---
name: yao-meta-skill
description: 把工作流、提示词、对话记录、文档或笔记整理成可复用的技能，也支持重构、评估和打包已有技能。适合在用户想新建 skill、优化 skill、补评测，或把重复流程沉淀成团队可复用能力时使用。
metadata:
  author: Yao Team
  philosophy: "structured design, evaluation loop, template ergonomics, operational packaging"
---

# Yao Meta Skill

Build reusable skill packages, not long prompts.

## Router Rules

- Route by frontmatter `description` first.
- Keep `SKILL.md` to routing plus the minimal execution skeleton.
- Push long guidance to `references/`, deterministic logic to `scripts/`, and evidence to `reports/`.
- Use the lightest process that still makes the skill reliable.

## Modes

- `Scaffold`: exploratory or personal.
- `Production`: team reuse with focused gates.
- `Library`: shared infrastructure or meta skill.

Mode rules: [Operating Modes](references/operating-modes.md), [QA Ladder](references/qa-ladder.md), [Resource Boundary Spec](references/resource-boundaries.md), [Skill Engineering Method](references/skill-engineering-method.md).

## Compact Workflow

1. Decide whether the request should become a skill, then choose the lightest archetype.
2. Capture the recurring job, outputs, trigger phrases, and exclusions.
3. Write the `description` early, then test route quality before expanding the package.
4. Add only the folders and gates that earn their keep: `trigger_eval.py`, `optimize_description.py`, `judge_blind_eval.py`, `resource_boundary_check.py`, `governance_check.py`, `cross_packager.py`.

Playbooks: [Skill Engineering Method](references/skill-engineering-method.md), [Skill Archetypes](references/skill-archetypes.md), [Gate Selection](references/gate-selection.md), [Non-Skill Decision Tree](references/non-skill-decision-tree.md), [Operating Modes](references/operating-modes.md), [Trigger And Eval Playbook](references/eval-playbook.md).

## Output Contract

Unless the user asks otherwise, produce:

1. a working skill directory
2. a trigger-aware `SKILL.md`
3. aligned `agents/interface.yaml`
4. optional `references/`, `scripts/`, `evals/`, `reports/`, and `manifest.json` only when justified
5. a short summary of boundary, exclusions, gates, and next steps

## Reference Map

- [Skill Engineering Method](references/skill-engineering-method.md)
- [Skill Archetypes](references/skill-archetypes.md)
- [Gate Selection](references/gate-selection.md)
- [Non-Skill Decision Tree](references/non-skill-decision-tree.md)
- [Operating Modes](references/operating-modes.md)
- [Governance Model](references/governance.md)
- [Resource Boundary Spec](references/resource-boundaries.md)
- [Trigger And Eval Playbook](references/eval-playbook.md)
