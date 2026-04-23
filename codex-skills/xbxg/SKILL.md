---
name: xbxg
description: 使用已安装的 `xbxg` CLI 访问超星 QMX xbxg 学工/宿管/迎新后台，适合做 doctor、自检、模块发现、当前账号信息读取、路由菜单读取、校区/年级/角色列表查询、导出任务查询与下载，以及在高阶命令缺失时走受控的 raw request。
---

# xbxg

先确认命令存在：

```bash
command -v xbxg
```

如果没找到，再检查 `~/.local/bin` 是否在 PATH 中。

## 起手顺序

第一步总是先跑：

```bash
xbxg --json doctor
```

它会告诉你：

- 当前 base URL 是什么
- token 或 cookie 是否存在
- 认证来源是 `flag`、`env`、`config` 还是 `missing`
- 根站点是否可达
- 未登录时会不会命中已知的 `29999` 认证失败形状

如果你现在还没有 token，下一步优先选这两个入口之一：

```bash
xbxg --json auth qr-url
printf '%s' '<password>' | xbxg --json auth login --username '<工号>' --password-stdin
```

## Auth

优先级：

1. `--token` / `--cookie`
2. 环境变量 `XBXG_TOKEN` / `XBXG_COOKIE`
3. `~/.xbxg/config.toml`

平时优先用环境变量或 `xbxg init`，不要把 token 长期写进 shell history。

初始化示例：

```bash
xbxg init --set-base-url https://xbxg2.qmx.chaoxing.com --set-token '<token>'
```

如果你已经从别处拿到了 token，也可以直接写入：

```bash
xbxg --json auth set-token --value '<token>'
```

清掉本地保存的 token 和 cookie：

```bash
xbxg --json auth clear
```

账号密码登录时优先用 `--password-stdin`。如果站点要求 CX captcha，再补 `--validate <value>`；如果不想处理 captcha，就改走 `auth qr-url` 生成的扫码地址。

## 发现路径

如果你还不知道这套站点大概有哪些模块，先看静态模块目录：

```bash
xbxg --json modules list
```

如果你已经有可用 token，下一步通常是看当前账号可见的真实路由树：

```bash
xbxg --json routes list --flat
```

## 安全只读路径

常用只读命令：

```bash
xbxg --json me
xbxg --json campuses list --page-num 1 --page-size 20
xbxg --json grades list --page-num 1 --page-size 20
xbxg --json roles list --page-num 1 --page-size 20
xbxg --json users list --page-num 1 --page-size 20
xbxg --json org-tree list
xbxg --json building-regions all
xbxg --json buildings all --ldssid <region-id>
xbxg --json room-types list --page-num 1 --page-size 20
xbxg --json house-masters list --page-num 1 --page-size 20
xbxg --json exports list --page-num 1 --page-size 20
xbxg --json downloads url <object-id>
```

如果你要把导出文件真的落地到本地：

```bash
xbxg --json downloads fetch <object-id> --out ./export.bin
```

## Raw 逃生口

当高阶命令还没覆盖到某个接口时：

```bash
xbxg --json request get /pedestal/user/getInfox
```

只有在用户明确要求某个 live 写操作时，才使用：

```bash
xbxg --json request post /some/path --body key=value
```

`request post` 是 live write，不是草稿模式。

## 不要做的事

- 不要在没有明确授权的情况下运行 `request post`
- 不要把完整 token 回显到对话里
- 不要把 `doctor` 里看到的认证失败误判成接口不存在；这套系统常见形状是 HTTP `200` + JSON `code=29999`

## 直接可复制示例

```bash
xbxg --json doctor
xbxg --json auth qr-url
xbxg --json modules list
xbxg --json routes list --flat
```
