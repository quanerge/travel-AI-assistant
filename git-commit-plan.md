# Git 提交拆分计划（5 个 commit）

> 在仓库根目录 `D:\github\旅游AI小助手` 下，用 Git Bash 逐段执行。
> 执行前先 `git status` 核对文件列表（本计划基于 2026-07-29 累积改动快照）。

## 重要说明（务必先看）
本次改动高度交织：**同一个文件同时含「功能改动」和「bug 修复」**。
- `server/routers/orders.py` 既有订单软删除（功能），又有 B3/B4（bug）；
- `miniprogram/pages/plan/*` 既有 UI 重排（功能），又有 B1（bug）；
- `server/routers/consult.py` 既有需求单闭环（功能），又有 B3（bug）；
- `server/main.py` / `admin/src/api/index.js` / `admin/src/layout/MainLayout.vue` 同时含客服消息 + 版本接口。

普通 `git add <文件>` 会把**整个文件**归入某一个 commit，无法在文件级把 bug 修复纯净拆出。
下面采用「文件按主导功能归组、互不重叠」的务实拆分（每个文件恰好出现一次）。
若你要求 bug 修复**绝对独立纯净**，需对重叠文件改用 `git add -p` 手动挑选 hunk（见文末附录）。

另外：`server/routers/consult.py` 若 `git status` 未列出，说明它已在更早的提交中，从 commit 1 去掉该行即可。

---

## Commit 1 — 需求单全闭环
```bash
git add server/routers/consult.py \
        server/models.py \
        server/schemas.py \
        server/database.py \
        server/utils/wechat.py \
        miniprogram/utils/api.js \
        miniprogram/utils/mock.js

git commit -F - <<'EOF'
feat: 需求单全闭环（顾问回复/方案附件/行程卡片/一键转订单/未读红点/订阅消息/软删除）

- ConsultRecord 模型补充 reply_content/attachments/itinerary/is_deleted/deleted_at
- 接口：GET /mine、GET /unread-count、POST /read、回复、POST /to-order、POST /delete（管理员+客户双角色）
- 微信订阅消息推送方案链接（P2）
- models/schemas/database 迁移同步新增列
EOF
```

## Commit 2 — 客服消息回传管理后台
```bash
git add server/routers/chat.py \
        admin/src/views/Chat.vue \
        admin/src/api/index.js \
        admin/src/router/index.js \
        admin/src/layout/MainLayout.vue \
        server/main.py

git commit -F - <<'EOF'
feat: 微信客服消息回传管理后台（/api/wechat/callback + 会话/回复）+ 后台版本接口

- 新增 ChatMessage 模型与 chat 路由（明文模式回调 GET 校验 / POST 存库）
- 管理后台 Chat.vue：会话列表（昵称/手机/未读红点）、消息气泡、回复、12s 轮询
- /api/version 版本接口；后台侧边栏版本展示（从后端取，失败兜底 V1.3）
- 路由与菜单接入（router/index.js、MainLayout.vue）
EOF
```

## Commit 3 — 小程序 UI 重排
```bash
git add miniprogram/pages/plan/plan.js \
        miniprogram/pages/plan/plan.wxml \
        miniprogram/pages/plan/plan.wxss \
        miniprogram/pages/routes/routes.js \
        miniprogram/pages/routes/routes.wxml \
        miniprogram/pages/routes/routes.wxss \
        miniprogram/pages/orders/orders.js \
        miniprogram/pages/orders/orders.wxml \
        miniprogram/pages/orders/orders.wxss \
        admin/src/views/Orders.vue

git commit -F - <<'EOF'
feat: 小程序 UI 重排（行程规划表单/线路筛选/订单删除）

- plan 表单：最少天数/人数改步进器，目的地/预算改 picker 下拉，并收集联系人姓名手机
- routes 列表：天数/价格区间 chip 筛选 + 出发地自动提取 + 重置，前端本地过滤
- orders：软删除按钮（catchtap 防冒泡）；管理后台 Orders.vue 删除按钮 + 确认
EOF
```

## Commit 4 — bug 修复（B1–B4）
```bash
git add server/routers/orders.py

git commit -F - <<'EOF'
fix: 静态审查发现的缺陷修复（B3/B4 + 关联 B1/B2）

- B3: 兜底补列逻辑先 db.rollback() 再 migrate() 重试（consult/orders）
- B4: confirm_deposit 删除 o.updated_at=None，改由 onupdate 自动维护
说明：B1（plan 表单补姓名手机）随 commit 3 的 plan.* 一并提交；
      B2（微信回调 GET 校验）随 commit 2 的 chat.py 一并提交；
      本 commit 聚焦 orders.py 的 B3/B4 修复。
EOF
```

## Commit 5 — 文档对齐
```bash
git add README.md \
        deploy.bat \
        "需求说明书_V1.3.md" \
        "需求说明书_修订版V1.1.md"

git commit -F - <<'EOF'
docs: 需求说明书对齐至 V1.3 并补充客服消息部署说明

- 新增 需求说明书_V1.3.md（与代码实现对齐，含第16章实现进度）
- 需求说明书_修订版V1.1.md 顶部加弃用指向说明
- README/deploy.bat 补充微信客服消息回传的公众平台配置步骤
EOF
```

## 推送
```bash
git push -u origin master
```

---

## 附录：若要求 bug 修复绝对纯净（git add -p）
对重叠文件逐个交互挑选 hunk（仅选 bug 相关 hunk 选 `y`，其余 `n`）：
```bash
# 先挑 bug hunk 进 index
git add -p miniprogram/pages/plan/plan.js      # 选 B1：name/phone 输入 + 校验
git add -p miniprogram/pages/plan/plan.wxml    # 选 B1：两个输入框
git add -p miniprogram/pages/plan/plan.wxss    # 选 B1：.text-input 样式
git add -p server/routers/orders.py            # 选 B3/B4：rollback + 删 updated_at
git add -p server/routers/consult.py           # 选 B3：rollback
git add -p server/routers/chat.py              # 选 B2：GET 校验 403
git commit -m "fix: B1-B4 静态审查缺陷修复"
# 再普通 add 剩余功能改动，分别提交功能 commit
```
