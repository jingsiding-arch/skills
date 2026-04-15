---
name: clone-website
description: 通过分析目标网站、提取资源和设计要素，在当前仓库里高还原地重建一个网站或落地页。适合在用户想克隆、复刻、逆向分析或尽量 1:1 重做某个网站时使用。
metadata:
  short-description: Clone a website into this repo
---

# Clone Website

Use this skill when the user wants a high-fidelity website clone in this project.

## Start Here

1. Read `TARGET.md` and confirm the target URL and scope.
2. Read `docs/codex/CLONE_WORKFLOW.md`.
3. Create missing output directories if needed:
   - `docs/research/components/`
   - `docs/design-references/`
   - `public/images/`
   - `public/videos/`
   - `public/seo/`
4. Verify the base project still compiles before large edits.

## Workflow

1. Inspect the live site with a browser-capable workflow when available.
2. Capture screenshots, design tokens, behaviors, and page topology.
3. Write the research docs before building components.
4. Implement the global foundation:
   - fonts
   - metadata
   - global CSS tokens
   - shared types
   - reusable icons
   - asset download helpers
5. Build sections from top to bottom, keeping each task narrowly scoped.
6. Validate after each major integration.

## Non-Negotiables

- Do not guess on visible design details if the live site can be inspected.
- Use real content and assets wherever feasible.
- Keep the build green with `npm run build`.
- Prefer small, composable components over one giant page file.
- Preserve responsiveness and visible interaction behavior.

## References

- `docs/codex/CLONE_WORKFLOW.md`
- `docs/research/INSPECTION_GUIDE.md`
- `AGENTS.md`
