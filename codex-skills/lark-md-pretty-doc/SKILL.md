---
name: lark-md-pretty-doc
version: 1.1.1
description: "将本地 Markdown 文件在正文零改写的前提下，创建为排版清晰的飞书云文档。适用于 PRD、方案、技术文档、会议纪要等从 .md 生成飞书文档，且要求保留原始标题、段落、表格、代码块与顺序不变，并默认以 editorial-warm 主题轻美化方式分块写入飞书。"
metadata:
  requires:
    bins: ["lark-cli", "python3"]
---

# Lark Markdown Pretty Doc

> **前置条件：**
> 1. 先阅读 [`../skills/lark-shared/SKILL.md`](/Users/homg/Documents/Codex/skills/.agents/skills/lark-shared/SKILL.md)
> 2. 再阅读 [`../skills/lark-doc/SKILL.md`](/Users/homg/Documents/Codex/skills/.agents/skills/lark-doc/SKILL.md)

这个 skill 专门解决一类高约束任务：

- 输入是一个现成的 `.md` 文件
- 要输出成飞书云文档
- **不允许修改原始 Markdown 正文的任何内容**
- 仍然要让飞书文档结构清晰、可读、稳定可创建

默认是“零改写、零删减、轻美化默认”模式；但如果**用户明确点名要求删除某个章节**，允许按**标题整段排除**，例如删除 `# 工程附表`。

默认目标补充规则：

- 如果用户没有指定 `--folder-token`、`--wiki-node` 或 `--wiki-space`，则默认创建到个人知识库 `my_library`
- 创建前默认先做一次飞书预检与 `--dry-run`
- 如果源 Markdown 已经手写了 `<callout ...>`，脚本会自动把最终 `beautify_mode` 从 `light` 降级为 `off`，避免生成嵌套 callout
- 默认主题是 `editorial-warm`
- `--preface-mode` 与 `--navigation-mode` 仅保留兼容旧调用，不再实际生成顶部导读块和阅读导航

## 快速路径

- 普通创建：`--input <abs.md> --wiki-space my_library`，默认先预检再 `--dry-run`
- 显式删章：额外传 `--omit-section-title "章节名"`
- 显式语义着色：额外传 `--inline-color-mode semantic-conservative`
- 冒号前标签加粗蓝色：额外传 `--label-prefix-style blue-bold`
- 不要流程图：额外传 `--flowchart-mode off`

## 不可破坏的约束

- **绝不修改源文件**：不改标题、不改标点、不改段落、不改换行、不改表格、不改代码块。
- **绝不改写正文**：不润色、不摘要、不补写、不删减、不重排。
- **例外仅来自用户显式指令**：如果用户明确说“删除某章节”，才允许按标题整段排除该章节。
- **默认不新增重型 AI 包装层**：不自动加顶部导读 `callout`、导入信息代码块、阅读导航、结构导图、章节提示。
- **允许新增的内容只有**：
  - 文档标题（来自文件名或用户显式指定）
  - 克制使用的分割线
  - 少量高亮块
  - 轻量分栏
  - 主题化但克制的章节包装
  - 按原文顺序分块 append 到飞书文档
- **默认允许轻美化**：在不改写正文的前提下，适度使用分割线、高亮块、分栏增强可读性。
- **默认主题是 `editorial-warm`**：目标是接近编辑手册/暖色白皮书气质，而不是普通蓝色说明块。
- **顶部导读块与阅读导航已移除**：即使旧参数传入，也只做兼容，不再生成。
- **只有用户明确要求增强排版时**，才允许显式开启结构导图、章节提示等额外辅助层。

## 显式章节排除

当用户明确要求删除某一章时，使用标题级排除，而不是正文级编辑。

推荐参数：

```bash
python3 /Users/homg/Documents/Codex/skills/lark-md-pretty-doc/scripts/create_lark_doc_from_md.py \
  --input "/absolute/path/to/file.md" \
  --wiki-space my_library \
  --omit-section-title "工程附表"
```

规则：

- 只允许删除**整段章节**
- 章节边界由标题层级决定
- 不允许为了“差不多”去删半段正文
- 如果同名标题出现多次，会删除所有匹配章节

更严格的判定标准见 [`references/preservation-contract.md`](references/preservation-contract.md)。

## 默认排版策略

默认使用“**editorial-warm 轻美化保真**”：

1. 以原始 Markdown 正文为主体创建飞书文档
2. 以暖橙系 `editorial-warm` 主题做克制包装
3. 长文档按标题/空行优先分块
4. 适度加入分割线，增强章节节奏
5. 对适合强调的短内容区使用少量高亮块
6. 对适合并列展示的短章节使用轻量分栏
7. 不自动插入顶部导读块、阅读导航、来源代码块

这满足你的要求：

- 原始 Markdown 正文保持不变
- 页面比纯正文更有视觉节奏
- 不引入之前那种过重的 AI 辅助层噪音
- 长文档仍可稳定创建

## 主题规则

这个 skill 默认使用 `editorial-warm`：

- **统一使用**一套暖色主题：`light-orange / orange / light-yellow / gray`
- 主题主要用于封面感标题区、摘要信息块、实现方案块、待确认块
- 默认**不新增大面积彩色正文**
- 默认**不新增行内颜色**
- 默认**不新增多套互相竞争的 callout 颜色**
- 如果源 Markdown 本身已经包含颜色语法，保留原文，但不要继续扩写新的颜色层级

这样做的目的是：

- 让 PRD / 技术文档更接近编辑手册式的暖色白皮书风格
- 让全文颜色使用规则一致
- 避免为了“好看”引入多套强调色，破坏正文的稳定阅读节奏

## 全局字体着色策略

如果用户明确希望“对某些字体内容上色”，使用**语义着色**，而不是自由发挥。

默认规则：

- **默认关闭**：为了保持正文零改写，正文内联着色默认不启用
- **显式开启**：只有用户明确要求“给某些内容上色”，才启用内联着色模式
- **局部克制**：优先给关键词着色，不给整段着色
- **避开高风险区域**：默认不自动改代码块、不自动改表格行、不自动改已有 XML 富文本标签

## 标签前缀样式

对于 PRD、方案、研发交付文档，常见会有这类短标签行：

- `页面定位：...`
- `使用角色：...`
- `前置条件：...`

如果用户明确希望这些“冒号前标签”更醒目，可开启：

```bash
--label-prefix-style blue-bold
```

效果是：

- 仅将冒号前的短标签渲染为**加粗 + 蓝色**
- 冒号后的正文保持原样
- 默认跳过表格、代码块、已有 `<text ...>` 富文本标签

默认仍为 `off`，避免在未明确允许时修改正文视觉层级。

## 流程图组件

如果文档里有标题明确包含：

- `流程`
- `流转`

则默认应优先尝试插入**飞书流程图 / 白板流程图组件**，而不是只保留纯文字步骤。

新增高优先级约束：

- **只允许在《功能需求明细》章节内部创建流程图**
- 即：只有标题路径中包含 `功能需求明细` 的子章节，才允许自动插入流程图 / 白板流程图组件
- `背景与目标`、`主流程与异常流程`、`业务规则`、`状态、通知与日志`、`待确认问题` 等章节，即使标题里出现“流程/流转”，也**不自动创建流程图**
- 若用户明确要求“全篇流程图”或点名某个非《功能需求明细》章节需要流程图，才允许突破这一默认限制

默认规则：

- `--flowchart-mode auto` 时，脚本只扫描《功能需求明细》章节内部、且标题包含“流程/流转”的子章节
- 若章节正文里能识别出编号步骤、项目符号步骤或流程表格，会自动生成 Mermaid 流程图
- 若步骤里能识别出 `是否 / 若 / 如需 / 超时 / 失败 / 冲突 / 不足 / 未...` 等判断信号，会优先使用判断节点（菱形）而不是一律画成长方形
- 先在对应标题后插入空白 whiteboard
- 再调用白板更新能力把流程图真正写入组件
- 若当前章节无法稳定抽出至少 2 个流程步骤，则不会硬造流程图，而是在结果里返回 warning

如果用户明确不要流程图，可显式关闭：

```bash
--flowchart-mode off
```

推荐语义：

- `red`：风险、禁止、失败、冲突、超时、驳回
- `orange`：待确认、待复核、依赖、前置条件、注意
- `green`：成功、已确认、已完成、已关闭、生效、通过
- 主题暖色：只用于自动新增的包装块，不默认批量作用于原始正文

推荐档位：

- `auto`：根据文档类型自动推荐，默认在 `semantic-conservative` 和 `semantic` 之间选更合适的一档
- `semantic-conservative`：**推荐用于 PRD**，只重点标红风险类、标橙待确认/依赖类，不默认给成功态上绿
- `semantic`：适合更强提示感的版本，会额外标绿色成功/生效类

不建议做法：

- 不要把“所有名词”都着色
- 不要给整张表每列都上色
- 不要同一语义混用多种颜色
- 不要在用户没明确允许时改正文颜色

## 推荐做法

优先使用本 skill 自带脚本：

```bash
python3 /Users/homg/Documents/Codex/skills/lark-md-pretty-doc/scripts/create_lark_doc_from_md.py \
  --input "/absolute/path/to/file.md" \
  --wiki-space my_library \
  --theme editorial-warm
```

常用附加参数速查：

| 需求 | 参数 |
| --- | --- |
| 自定义标题 | `--title "文档标题"` |
| 指定目标位置 | `--folder-token ...` / `--wiki-node ...` / `--wiki-space ...` |
| 只预演不创建 | `--dry-run` |
| 删除指定整章 | `--omit-section-title "工程附表"` |
| 正文语义着色 | `--inline-color-mode semantic-conservative` / `semantic` / `auto` |
| 冒号前标签加粗蓝色 | `--label-prefix-style blue-bold` |
| 禁用自动流程图 | `--flowchart-mode off` |
| 开启结构导图或章节提示 | `--mindmap-mode auto` / `--section-hint-mode auto` |

## 脚本能力

脚本位于：

- [`scripts/create_lark_doc_from_md.py`](scripts/create_lark_doc_from_md.py)

它会：

- 读取本地 Markdown 文件
- 保留正文原文
- 若用户明确要求，则按标题整段排除指定章节
- 若用户明确要求，则按统一语义规则给部分关键词做内联着色
- 若用户选择 `auto`，会先判断文档类型，再自动在克制版和增强版之间择一
- 默认使用 `editorial-warm` 主题对标题区、说明块、实现方案块做暖色轻包装
- 自动做“按标题优先、且不切开 fenced code block”的安全分块
- 遇到超长 fenced code block 时，允许单个追加块临时超过“偏好预算”，优先保证代码围栏完整
- 调用 `lark-cli docs +create`
- 必要时继续调用 `lark-cli docs +update --mode append`
- 输出结构化 JSON 结果，包含 `doc_id`、`doc_url`、分块数量、执行模式

## 当你在 agent 中使用这个 skill 时

按这个顺序执行：

1. 确认 Markdown 文件绝对路径存在。
2. 先执行飞书预检：`lark-cli doctor`；若使用 `--as user`，再执行 `lark-cli auth status`。
3. 预检失败时先回到 `lark-shared` 完成配置或认证，不要继续假装创建成功。
4. 确认目标位置；若用户未指定，默认使用 `--wiki-space my_library`。
5. 默认先执行一次 `--dry-run`，确认预检、目标位置、分块数和最终 `beautify_mode`。
6. 默认使用 `--as user --theme editorial-warm`；若源文档已含 `<callout ...>`，脚本会自动把 `beautify_mode` 降级为 `off`。
7. `--preface-mode` 与 `--navigation-mode` 只保留兼容，不要主动传。
8. 只有用户明确要求时，才开启 `--omit-section-title`、`--inline-color-mode`、`--label-prefix-style`、`--mindmap-mode`、`--section-hint-mode`。
9. 优先执行脚本，不手写大段 `lark-cli docs +create --markdown "..."`。
10. `--dry-run` 和飞书预检都通过后，继续执行真实创建，不要停在预演结果。
11. 创建完成后，把 `doc_id`、`doc_url`、目标位置和最终采用的排版/着色档位返回给用户。

## 脚本默认保障

- 长文档默认分块创建，避免一次性大 payload 失败。
- 分块时不在 fenced code block 内切开；超长代码块允许单块临时超过预算。
- 中途 append 失败时，至少保留已创建文档和已成功写入的块。
- 目标位置支持个人知识库、知识库节点、云空间文件夹；未显式指定时默认回落到 `my_library`。
- 默认输出 JSON 摘要，方便审计与复盘。
- 默认只创建新文档并追加，不对现有文档执行 overwrite。
- 源 Markdown 已含 `<callout ...>` 时，自动关闭轻美化，避免飞书出现嵌套 callout 风险。
- `auto` 模式会输出最终采用的档位与判断理由。

## 自检与回归

- 修改本 skill 的说明、agent 入口、样例或脚本后，默认先运行：
  `python3 scripts/lint_skill_consistency.py`
- 做 dry-run 回归时，运行：
  `python3 scripts/eval_dry_run_samples.py`
- 回归至少要覆盖：
  - 默认创建到 `my_library`
  - `preflight.ready` 为真
  - 手写 `<callout ...>` 时自动把 `beautify_mode` 降为 `off`
  - `--omit-section-title` 会被正确应用

## 不该做的事

- 不要把原文改写成“更像飞书风格”的版本
- 不要因为排版好看就改章节顺序
- 不要删除原文中的一级标题、表格、列表或代码块
- 不要在用户没明确要求时，擅自删除“工程附表”或任何其他章节
- 不要在用户没明确要求时，擅自给正文关键词上色
- 不要生成顶部导读块或阅读导航
- 不要在用户没明确要求时，擅自插入结构导图或章节提示
- 不要为了“用了分栏和高亮块”而把整篇文档包装成营销海报风
- 不要把正文包进 `callout` 里
- 不要对现有文档用 `overwrite` 重建

## 直接 CLI 兜底

如果脚本不可用，才手动执行：

1. 用 `lark-cli docs +create` 创建第一段正文
2. 再用 `lark-cli docs +update --mode append` 追加剩余原文
3. 每一段正文都必须来自源 Markdown 的原始切片，不得改写
