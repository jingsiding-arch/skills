# Codex Skills Share

这个仓库用于共享一套可复用的 Codex 技能，包括：

- `codex-skills/`：放到 `~/.codex/skills/` 的自定义技能
- `agents-overrides/`：放到 `~/.agents/skills/` 的内置技能中文显示配置覆盖层
- `scripts/install.sh`：一键安装脚本

## 包含内容

- 11 个自定义技能目录
- 22 个内置技能的中文显示名覆盖配置

## 安装

在仓库根目录执行：

```bash
bash scripts/install.sh
```

默认会把文件安装到：

- `~/.codex/skills`
- `~/.agents/skills`

安装完成后，重启 Codex 以加载新的技能与显示名称。

## 更新方式

如果这个仓库里的内容有更新，同事拉取最新代码后再次执行：

```bash
bash scripts/install.sh
```

## 说明

- 这个仓库不会覆盖内置技能的主体逻辑，只会补充 `agents/openai.yaml` 这类中文显示配置。
- 自定义技能会同步到 `~/.codex/skills/` 下对应目录。
- 如果你们团队后续想统一维护技能，建议直接在这个仓库里修改后再分发。
