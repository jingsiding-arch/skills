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
- 对每条样例执行 `create_lark_doc_from_md.py --dry-run`
- 检查预检状态、`beautify_mode`、章节排除结果、分块数量等关键字段

## 3. 当前覆盖

- 默认落点与 dry-run 正常返回 JSON
- `preflight.ready` 为真
- 手写 `<callout ...>` 时自动把 `beautify_mode` 从 `light` 降为 `off`
- `--omit-section-title` 会被正确应用

## 4. 仍需人工复核

- 实际飞书创建后的视觉效果
- 长文档下分块节奏是否理想
- 流程图 whiteboard 的内容质量
