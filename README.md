# Codex Skills Share

这个仓库用于共享一套可复用的 Codex 技能，包括：

- `codex-skills/`：放到 `~/.codex/skills/` 的自定义技能
- `agents-overrides/`：放到 `~/.agents/skills/` 的内置技能中文显示配置覆盖层
- `scripts/install.sh`：一键安装脚本

## 包含内容

- 9 个自定义技能目录
- 22 个内置技能的中文显示名覆盖配置

## 安装

在仓库根目录执行：

```bash
bash scripts/install.sh
```

如果只想安装部分技能，也可以在命令后面直接带技能目录名：

```bash
bash scripts/install.sh enhance-prompt
bash scripts/install.sh enhance-prompt design-md
```

默认会把文件安装到：

- `~/.codex/skills`
- `~/.agents/skills`

安装完成后，脚本会自动对刚安装的自定义 skills 做一次**风险扫描**，并根据各个 `SKILL.md` 里声明的 `recommended-skills` 输出“建议一起安装的 companion skills”及用途说明，然后再提示你重启 Codex。

默认行为：

- **会扫描**
- **不会因为发现风险而中断安装**

如果你希望发现高风险时直接让安装命令失败，可以这样执行：

```bash
SKILL_RISK_FAIL_ON=high bash scripts/install.sh
```

可选阈值：

- `none`：只报告，不阻断（默认）
- `medium`
- `high`
- `critical`

你也可以单独运行扫描脚本：

```bash
python3 scripts/scan-skills-risk.py codex-skills
python3 scripts/scan-skills-risk.py ~/.codex/skills/react-components
```

说明：

- 这是**静态启发式扫描**，不是绝对安全证明
- 它主要检查：联网下载、安装依赖、浏览器自动化、提权、写文件、动态执行等模式
- 建议对 `HIGH` / `CRITICAL` 结果做人工复核

## 更新方式

如果这个仓库里的内容有更新，同事拉取最新代码后再次执行：

```bash
bash scripts/install.sh
```

详细更新记录见 [CHANGELOG.md](./CHANGELOG.md)。

## 说明

- 这个仓库不会覆盖内置技能的主体逻辑，只会补充 `agents/openai.yaml` 这类中文显示配置。
- 自定义技能会同步到 `~/.codex/skills/` 下对应目录。
- 如果某个 skill 在 frontmatter 里声明了 `recommended-skills`，安装时会提示建议同时安装哪些 companion skill，以及它们分别用于什么场景。
- 如果你们团队后续想统一维护技能，建议直接在这个仓库里修改后再分发。
