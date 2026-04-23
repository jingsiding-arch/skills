# Evals Usage

## 1. 静态一致性检查

```bash
python3 scripts/lint_skill_consistency.py
```

## 2. Dry-run 回归

```bash
python3 scripts/eval_dry_run_samples.py
```

它会：

- 读取 `evals/samples.jsonl`
- 调用 `scripts/sync_lark_module_prd_doc.py --dry-run`
- 检查创建/替换模式、飞书预检、关键默认参数和最小输出长度

## 3. 当前覆盖

- 默认新建与默认整篇替换模式
- `preflight.ready` 为真
- `label_prefix_style=blue-bold`
- `flowchart_mode=auto`
- 最小 chunk / 长度正常返回
- 甘特图脚本能把结构化排期计划转换成 Base 建表和 gantt 视图配置动作

## 4. 甘特图 dry-run 回归

```bash
python3 scripts/eval_gantt_plan_samples.py
```

它会：

- 读取 `evals/gantt_samples.jsonl`
- 调用 `scripts/create_lark_dev_gantt.py --dry-run`
- 检查任务数、模块数、总工作量、命令数量和 gantt 视图名称
