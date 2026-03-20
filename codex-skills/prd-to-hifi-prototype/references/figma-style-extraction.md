# Figma 作为样式参考（Style Extraction）

目标：让原型的视觉（颜色、字号、间距、组件风格、布局）尽量与 Figma 对齐，同时保持原型代码可维护。

## 需要用户提供什么

- Figma 文件链接（`design` 或 `proto` 都可以）
- 关键页面的 Frame 链接（尽量包含 `node-id`），建议先给 P0 页面 1-3 个
- 若有设计系统/变量（Variables/Token），提供对应入口或说明
- 若权限受限，请用户开通只读访问，或导出关键页面截图

## 从链接中拿到可用的 nodeId

工具调用需要 `fileKey` 和 `nodeId`：

- `fileKey`：URL 中 `/design/<fileKey>/...` 或 `/proto/<fileKey>/...` 的那段
- `nodeId`：URL 里 `node-id=1-2` 这种格式，将 `-` 替换为 `:`（例如 `1-2360` -> `1:2360`）

常见情况：

- 用户给的是原型链接，但 `node-id=0-1` 或者没有 `node-id`：
  - 先用 `mcp__figma__get_metadata(fileKey, nodeId="0:1")` 列出页面下的顶层 Frame
  - 从返回的 `<frame id="...">` 里找到目标页面的 Frame id（例如 `p1xxx`）
  - 再对该 Frame id 调 `mcp__figma__get_design_context` / `mcp__figma__get_screenshot`

## 抽取流程（建议顺序）

1. 把每个 `pageKey` 绑定到一个 Figma Frame（记录在 UI manifest 的 `Figma节点` 列）
2. 逐个 Frame 获取设计上下文（布局、样式、截图、资产）：
   - 用 `mcp__figma__get_design_context` 获取 node 的截图与结构化信息
   - 必要时用 `mcp__figma__get_screenshot` 做局部校对
3. 若项目使用 Figma Variables：
   - 用 `mcp__figma__get_variable_defs` 抽取颜色/字号/间距等 token（只抽取本模块需要的最小集合）
4. 将 token 落地到前端：
   - 优先：用 Ant Design 的 theme token/组件 token 对齐主色、圆角、字号、间距、阴影
   - 补充：用 CSS variables + 少量页面级 CSS 精修布局与视觉细节
5. 将 Figma 资产落地：
   - 图标/插图：按需要导出并放入 `src/assets/` 或 `public/`，避免整包导出

## 规则与降级策略

- Figma 是视觉事实来源，但 PRD 是交互/业务事实来源；冲突时先问用户。
- 如果拿不到 Figma 权限或 Frame 不完整：
  - 先用 AntD 默认主题 + 页面级 CSS 还原结构与关键交互
  - 在说明中标注：哪些视觉是“未对齐（TBD）”
- 不要“凭感觉补色值/字号”；缺 token 时用 `TBD` 标注并提出最少问题。
