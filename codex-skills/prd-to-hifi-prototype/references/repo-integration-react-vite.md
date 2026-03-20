# 在 React + Vite 项目中落原型（Repo Integration）

目标：把原型代码“接入现有项目”，保证 `npm run dev` 可直接访问到新页面。

## 1. 先识别路由方式

- 如果项目使用 `react-router`：
  - 在现有 router 文件中新增 routes，并接入到现有导航（Menu/侧边栏/顶部 Tab）。
- 如果项目没有 `react-router`，而是用 hash/状态切换：
  - 常见写法是读取 `window.location.hash`，将 hash 映射到页面 key，再条件渲染页面组件。
  - 此时应新增：`pageKey` 类型、`hashToPage()` 映射、以及页面渲染分支。

## 2. 推荐的原型代码组织（模块隔离）

- `src/prototypes/<moduleKey>/pages/*`：页面（列表/详情/审批/设置等）
- `src/prototypes/<moduleKey>/mock/*`：mock store + mock API
- `src/prototypes/<moduleKey>/types/*`：核心类型与枚举
- `src/prototypes/<moduleKey>/components/*`：模块私有组件（可选）

## 3. 原型导航接入方式

- 最小可用：新增一个“原型入口页”（Prototype Home），列出页面清单并以 hash/route 跳转。
- 若项目已有顶部导航/侧边栏：尽量复用已有组件，保持视觉一致。

## 4. Mock API 与状态的基本约束

- 原型默认不依赖真实后端；mock API 用 Promise + delay 模拟网络。
- 对“可演示”的关键动作必须可用：新增/编辑/删除/审批/状态流转至少覆盖主流程。
- 需要“可重复演示”时，mock store 可选持久化到 `localStorage`（标明这是原型策略）。
