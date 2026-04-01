# Changelog

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
