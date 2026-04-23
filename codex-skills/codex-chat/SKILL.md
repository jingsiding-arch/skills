---
name: codex-chat
description: 检索本机已归档的 Codex 对话记录，适合在用户想回溯旧线程、从历史对话提炼 prompt、基于既有对话创建 skill、或根据过往对话优化 skill 时使用。
---

# Codex Chat

默认先确认命令可用：

```bash
command -v codex-chat
```

若不存在，提示先到 `/Users/homg/code/clis/codex-chat` 执行：

```bash
make install-local
```

## 首次使用顺序

1. 先做健康检查：

```bash
codex-chat --json doctor
```

2. 若索引不存在或过旧，先重建：

```bash
codex-chat index build
```

3. 再按目标检索：

```bash
codex-chat search "课堂考勤"
```

## 常用路径

- 找线程列表：

```bash
codex-chat threads list --query "skill"
```

- 找值得沉淀成 skill 的历史线程：

```bash
codex-chat skills suggest --query "skill" --limit 10
```

- 把某个线程整理成 skill 简报：

```bash
codex-chat skills brief <thread-id> --format markdown --out /tmp/skill-brief.md
```

- 找具体消息片段：

```bash
codex-chat search "优化 skill" --limit 20
```

- 查看某个线程的干净上下文：

```bash
codex-chat show <thread-id>
```

- 导出成 Markdown，方便继续整理：

```bash
codex-chat export <thread-id> --format markdown --out /tmp/thread.md
```

- 如果目标是“从历史对话创建或优化 skill”，优先顺序通常是：
  1. `skills suggest`
  2. `show` 或 `export`
  3. `skills brief`
  4. 再把简报交给 `skill-creator` 或手动继续编辑

## 配置

默认读取 `~/.codex` 下的历史数据，索引默认写到 `~/.codex/codex-chat/index.sqlite`。

如需改路径，可用：

```bash
codex-chat init --codex-home ~/.codex --index-db ~/.codex/codex-chat/index.sqlite
```

也可临时通过 `--codex-home` 或 `--index-db` 覆盖。

## SQL 逃生口

需要更细的筛选或统计时，可运行只读 SQL：

```bash
codex-chat sql "select thread_id, thread_name from threads order by updated_at desc limit 10"
```

除非用户明确要求，不要直接写修改型 SQL。
