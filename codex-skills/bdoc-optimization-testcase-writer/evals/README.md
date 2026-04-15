# Evals Usage

## 1. 静态一致性检查

```bash
python3 scripts/lint_skill_consistency.py
```

## 2. 输出结构评测

单条输出：

```bash
python3 scripts/eval_output_against_sample.py \
  --sample-id yx-001 \
  --output /path/to/yx-001.md
```

批量输出：

```bash
python3 scripts/eval_output_against_sample.py \
  --outputs-dir /path/to/outputs
```

批量模式下，输出目录中的文件名需为：

- `yx-001.md`
- `sg-001.md`
- `xg-001.md`
- `zz-001.md`
- `lx-001.md`

## 3. 当前评测覆盖

- `直接执行 / 深度交互` 双段结构
- `must_include` 中的硬性结构标记
- 新旧测试表头检查
- 非必要截图占位检查
- 测试用例与待确认项的配套出现

## 4. 仍需人工复核

- `must_reason_about` 的论证深度
- `must_avoid` 中较抽象的策略偏差
- 方案是否真的更轻、更省、更符合业务目标
