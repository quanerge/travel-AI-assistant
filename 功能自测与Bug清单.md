# 功能自测与 Bug 清单（静态审查版）

> 审查时间：2026-07-29
> 审查方式：**静态代码审查**（逐文件核对接口契约与逻辑）
> ⚠️ 说明：本环境命令通道故障，无法真正启动后端 / 构建前端 / 跑 curl，因此以下为**代码层逻辑核查**，非运行时测试结果。建议本机按文末清单做一次冒烟测试。

---

## 一、已核查且逻辑正确的功能（✅ 无 bug）

| 模块 | 核查点 | 结论 |
|---|---|---|
| 客服消息回传 | chat.py 路由 `/api/wechat/callback`(GET/POST)、`/api/admin/chat/{sessions,messages,reply,read}`；Chat.vue 字段与接口一一对应；轮询/已读/回复逻辑 | ✅ |
| 微信下发 | wechat.py `send_custom_message` / `send_subscribe_message` 失败静默降级 | ✅ |
| 需求单闭环 | 创建/列表/我的/未读红点/标记已读/顾问回复/转订单/软删除 全链路逻辑 | ✅ |
| 软删除过滤 | 列表/详情 `or_(is_deleted==False, is_deleted.is_(None))` 兼容旧 NULL 行 | ✅ |
| 删除护栏 | 需求单：已转订单(done)不可删；订单：已确认/已付定金/已完成不可删 | ✅ |
| 手机号加密 | 存储 `enc:` 前缀，schemas `phone` 有 `decrypt_phone` validator，crypto 向后兼容 | ✅ |
| 小程序接口路径 | `config.baseUrl` 已带 `/api`，`request('/consult/mine')` → `.../api/consult/mine` 与后端对齐（不 404） | ✅ |
| 线路筛选 | `routes.js` 用 `days/price/category/departure/cover/name/destination` 与 Route 模型字段名完全一致 | ✅ |
| 行程规划提交 | `plan.js` 拼 content 文本 → `submitPlan`，后端只存 content，契约一致 | ✅ |
| 我的咨询 | 列表/已读/转单/删除/附件 `absUrl` 补全逻辑正确 | ✅ |
| 版本接口 | 后端 `/api/version` 与前端 `getVersion` 对齐 | ✅ |
| 自动迁移 | `database.migrate()` 对"列已存在"用 `except OperationalError: pass` 容错 | ✅ |

---

## 二、发现的 Bug / 缺陷

### 🔴 严重（功能无法达成）

**B1：从「智能规划(plan)」提交的需求单无法一键转订单**

- **现象**：用户在 `plan` 页提交需求单 → 顾问回复方案 → 用户点"对此方案下单" → 后端返回 `400 需求单缺少联系人姓名/手机，无法下单`。
- **根因**：
  1. `miniprogram/pages/plan/plan.js` 的表单**不收集姓名/手机号**，提交 payload 只有 `destination/days/person/budget/interest`；
  2. `consult_to_order`（`server/routers/consult.py`）要求 `rec.name` 与 `rec.phone` 非空；
  3. 演示模式下 `wx-login` 用 `dev_` 前缀派生 openid 落库，`User.phone` 默认空，`_attach_customer_identity` 也补不到手机。
- **影响范围**：`consult.js`（在线留言）表单收集了 name/phone，能正常转单；唯独 `plan` 入口不行——两入口不对称。
- **修复建议（任选）**：
  - 方案 A（推荐）：在 `plan.wxml` 增加"联系人姓名/手机号"两个输入框，`plan.js` 提交时一并带上；
  - 方案 B：放宽 `consult_to_order`，姓名手机缺失时回退到 `User.nickname/phone`，仍缺则提示用户先去"我的"绑定手机（但订单必须有手机，最终仍需用户补全）。

---

### 🟡 设计 / 正确性缺陷（不崩溃，但需注意）

**B2：微信回调 GET 校验形同虚设**

- **位置**：`server/routers/chat.py` `wechat_verify`
- **问题**：无论 `signature` 是否匹配，都返回 `echostr`。导致公众平台 Token 配错时也能"配置成功"，**掩盖错误配置**，排障时难以发现。
- **修复**：校验失败时不回显 `echostr`（返回空或 400），让微信报配置错误。

**B3：兜底补列逻辑缺 rollback**

- **位置**：`consult.py` 的 `create_consult`/`update_consult`/`delete_consult` 与 `orders.py` 的 `delete_order`
- **问题**：`except` 分支里 `commit()` 失败后立即 `migrate()` + 再次 `commit()`，未先 `db.rollback()`。正常路径（app 启动时已 `migrate()`，列已存在）不会触发；但若真走到 except，session 可能失效导致二次 commit 抛错。
- **修复**：`except` 内先 `db.rollback()` 再 `migrate()` + `commit()`。

**B4：`confirm_deposit` 把 `updated_at` 置 NULL**

- **位置**：`server/routers/orders.py:105` `o.updated_at = None`
- **问题**：触发 `onupdate=datetime.utcnow` 把更新时间存成 NULL（应为最近时间）。无害但不规范。
- **修复**：删除该行，让其自然 onupdate。

---

## 三、验证限制与待办

- **无法运行验证**：命令通道故障，未做 `py_compile` / 启动 / 构建；以上结论基于源码静态核对。
- **本机冒烟测试建议**（命令恢复或你本机执行）：
  1. 后端：`python -c "import server.main"` 语法自检；启动后 `curl /api/version`、`curl /api/wechat/callback?...&echostr=OK` 应返回 `OK`。
  2. 小程序：`deploy.bat` 重建后，微信开发者工具模拟器验证 plan 提交→后台回复→myConsult 转单（重点验证 B1）。
  3. 客服消息：需公网 + 公众平台「消息推送」开启（明文模式 + Token）才能真正收消息。
- **git 状态**：上述功能代码与本文档仍未被提交（累积约 38 文件），待命令通道恢复或你本机 `git add -A && commit && push`。
