# Changelog

## 2026-04-15

### Add yao-meta-skill to shared pack with explicit risk note

本次更新把 `yao-meta-skill` 也同步进共享仓库，补齐与本地 `~/.codex/skills` 的最后一个差异项。

更新内容：

- 新增共享技能目录 `codex-skills/yao-meta-skill`
- 当前共享仓库中的自定义技能总数更新为 38 个
- 同步时排除了本地 `.git` 元数据与缓存目录
- 风险扫描结果中，该技能仍保留一个 `CRITICAL` 项：`Makefile` 中存在 `rm -rf dist tests/tmp tests/tmp_snapshot` 的清理命令，后续安装和使用时应人工知悉并审查

## 2026-04-15

### Sync remaining local custom skills into shared pack

本次更新把本地 `~/.codex/skills` 里尚未进入共享仓库的剩余自定义技能统一同步到 `codex-skills/`，让团队安装源和个人常用技能集保持一致。

更新内容：

- 新增 27 个共享技能目录，包括文档处理、网页访问、技能工程、研究分析、内容创作与 GitHub 工作流相关能力
- 当时共享仓库中的自定义技能总数更新为 37 个
- 同步时排除了 `.DS_Store` 和 `__pycache__` 等本地缓存文件
- 清理了误同步进去的嵌套 `.git` 目录和 `node_modules`
- `yao-meta-skill` 在这一批里暂未纳入共享仓库，后续已单独同步并记录风险说明
- 后续安装 `bash scripts/install.sh` 时会一起安装这些新增技能

## 2026-04-15

### Add bdoc optimization skill to shared pack

本次更新把 `bdoc-optimization-testcase-writer` 同步进共享技能仓库，方便团队统一安装和分发。

更新内容：

- 新增共享技能目录 `codex-skills/bdoc-optimization-testcase-writer`
- 同步了该技能所需的 `agents/`、`assets/`、`references/`、`evals/` 和 `scripts/` 资源
- `README.md` 中的自定义技能数量更新为 10 个

## 2026-04-15

### Add companion skill suggestions during install

本次更新为技能安装流程补充了“依赖/搭配技能提示”能力，避免用户只安装主 skill 时漏掉关键的上游或协作 skill。

更新内容：

- `scripts/install.sh` 支持只安装指定 skill，例如 `bash scripts/install.sh enhance-prompt`
- 新增脚本 `scripts/show-skill-recommendations.py`
- 安装完成后会读取 `SKILL.md` frontmatter 中声明的 `recommended-skills`
- 如果某个 skill 建议搭配其他 skill，会在安装时提示“建议同时安装什么，以及这些 skill 分别用于做什么”
- `enhance-prompt` 和 `prd-to-hifi-prototype` 补充了 companion skill 声明示例
- `README.md` 补充了按技能安装与 companion skill 提示说明

## 2026-04-01

### Add post-install skill risk scanning

本次更新为 `skills` 安装流程增加了安装后风险扫描能力，帮助在导入自定义 skill 后快速发现潜在高风险行为。

更新内容：

- 安装脚本 `scripts/install.sh` 现在会在安装完成后自动执行一次 skill 风险扫描
- 新增扫描脚本 `scripts/scan-skills-risk.py`
- `README.md` 补充了风险扫描说明、阈值配置和单独运行示例

扫描特点：

- 默认会扫描，但不会因为发现风险而中断安装
- 可通过 `SKILL_RISK_FAIL_ON` 配置失败阈值
- 支持 `none`、`medium`、`high`、`critical`
- 可单独对某个 skill 或整个目录执行静态扫描

使用示例：

```bash
bash scripts/install.sh
```

高风险即失败：

```bash
SKILL_RISK_FAIL_ON=high bash scripts/install.sh
```

单独扫描：

```bash
python3 scripts/scan-skills-risk.py codex-skills
python3 scripts/scan-skills-risk.py ~/.codex/skills/react-components
```

说明：

- 这是静态启发式扫描，不代表绝对安全
- 主要检查联网下载、依赖安装、浏览器自动化、提权、文件写入、动态执行等模式
- 建议对 `HIGH` 和 `CRITICAL` 结果做人工复核
