# 旅途管家 · 部署指南

> 适用对象：`需求说明书_修订版V1.1.md` 对应的代码包（微信小程序前端 + FastAPI 后端）。
> 本文覆盖**生产部署**全流程：后端上线、前端发布、微信后台配置、安全清单。
> **想先在本机跑起来看效果？** 直接看第 0.5 章「本地开发联调」，无需服务器、无需备案。

---

## 0.5 本地开发联调（零成本，推荐先跑通）

本机三件套：**后端 API**（FastAPI :8000）+ **管理后台**（Vue :5173）+ **小程序**（微信开发者工具）。

### A. 后端（已在本机验证可跑）

```bash
cd server
# 用已生成的隔离 Python 环境（或自建 venv）
..\..\.workbuddy\binaries\python\envs\default\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
# 或双击 server/start_local.bat
```

- 首次需建表灌数据：同环境执行 `python seed.py`。
- 验证：`http://127.0.0.1:8000/docs`（Swagger，可在线试接口）。
- 接口文档：`/docs`（Swagger）、`/redoc`、`/openapi.json`。

### B. 管理后台（Vue3 + Vite，已构建验证通过）

```bash
cd admin
npm install          # 仅首次
npm run dev -- --port 5173     # 开发预览，访问 http://127.0.0.1:5173
# 或生产构建：npm run build → 产物在 admin/dist/，用任意静态服务器托管
```

- `vite.config.js` 已配 `/api` 代理到 `http://127.0.0.1:8000`，所以浏览器直接开 5173 即可连真实后端；`base` 已设为相对路径 `./`，部署到任意子目录 / CloudStudio 都不会 404。
- **生产托管**：`npm run build` 产物在 `admin/dist/`，用 nginx 托管该目录并把 `/api` 反向代理到后端（见 `server/nginx.conf`）即可。最新构建已含 **用户管理**（`/users`）、**系统设置**（`/settings`）两个新后台页面，以及客户/订单手机号的 **默认脱敏（138****8888，点「显示」才出全号）**。
- **一键脚本**：仓库根 `deploy.bat`（Windows 双击：自动 `npm install` + `npm run build` + **先杀掉占用 8000 端口的旧后端进程**（修复「界面显示 `enc:` 密文」问题）+ 启动后端 + 跑手机号迁移，最后自动打开 `http://127.0.0.1:8000/ui/`）。
- **轻量重启**：若仅后端改了代码、前端无需重建，直接双击 `restart-backend.bat`（同样先杀旧进程再重启，约 5 秒即可解决 `enc:` 乱码，无需等待 `npm build`）。
- 登录账号：`admin / admin123`（密码已用 **bcrypt** 哈希，登录后签发 **JWT**，后台接口均校验 `Authorization: Bearer <token>`；正式环境请务必改密码）。
- **一步到位打开后台**：后端启动后若 `admin/dist` 已构建，访问 `http://127.0.0.1:8000/ui/`（根路径 `/` 会自动跳转）即可，无需另起静态服务器——后端已直接托管前端，`/api` 同源无跨域。
- 演示顾问账号（用户管理页可管理）：`advisor / advisor123`（角色 advisor，仅能看到被分配的功能；用户管理页自身仅超管可见）。

### C. 微信小程序（用户端）

两种玩法：

1. **纯看交互（最简单）**：小程序 `utils/config.js` 设 `useMock=true`，开发者工具导入即能预览全部页面，连后端都不用开。
2. **联调真实后端（已配好）**：`config.js` 设 `useMock=false`、`baseUrl='http://127.0.0.1:8000/api'`，按下方第 0.6 章导入，即可走本机真实后端。

> 端口速记：后端 8000（API）｜ 管理后台 5173（Web）｜ 小程序在开发者工具里跑。

---

## 0.6 微信开发者工具（小程序运行环境）

微信小程序**只能在微信开发者工具里运行/预览**，无法像网页一样双击打开。本机尚未安装，按下面装：

1. **下载**：https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html → 选 **稳定版 / Windows 64 位** exe。
2. **安装**：双击一路下一步（默认装到 `C:\Program Files (x86)\Tencent\微信web开发者工具`）；首次启动用微信扫码登录（个人号即可）。
3. **导入项目**：工具里「导入项目」→ 目录选 `miniprogram/` → **AppID 选「测试号」**（无需注册，本地预览够用；正式发布才需自己的 AppID）。
4. **关键一步**：「详情 → 本地设置」勾选 **不校验合法域名、web-view、TLS 版本以及 HTTPS 证书**（否则 `127.0.0.1` 会被微信拦截）。
5. 点「编译」→ 模拟器即出页面；可点「真机预览」扫码在手机看。

> 装完后可用 CLI 一键打开（避免手动点）：
> `微信web开发者工具路径/cli.bat -o 项目目录` 或 `-p 项目目录`（preview）。我可帮你拼好这条命令。

---

## 0. 关键前提（务必先看）

微信小程序有如下**硬性约束**，不满足无法联调真实后端：

1. **请求域名必须是 HTTPS**，且域名已完成 **ICP 备案**。`http://`、未备案域名、IP 直连均会被拦截。
2. 域名须在 **微信公众平台 → 开发管理 → 开发设置 → 服务器域名** 中登记为「request 合法域名」。
3. 当前 `project.config.json` 的 `appid` 为 `wxefd32155fa7d0442`（你自己的 AppID，可直接真机预览/上传）。发布前请确认该 AppID 已完成小程序认证与类目资质；若用测试号体验，导入时切「测试号」即可。

> 因此「部署」= 把后端放到一个**已备案 HTTPS 域名**下 + 把小程序上传审核发布。

---

## 1. 后端部署（三选一）

### 方案 A：Docker 部署（★ 推荐，最省心）

前提：服务器已装 Docker 与 Docker Compose。

```bash
cd server
cp .env.example .env          # 编辑 .env：填真实 DATABASE_URL 与 CORS_ORIGINS
docker compose up -d --build  # 构建并启动 api + mysql
docker compose exec api python seed.py   # 首次初始化演示数据/建表
```

- 镜像已用 `gunicorn + uvicorn worker` 提供并发（`-w 4`）。
- 数据库默认 MySQL（`docker-compose.yml` 已含），数据持久化在 `db_data` 卷。
- 访问：`https://你的域名/`（需前端再套 nginx 见下方 §3）。

### 方案 B：云服务器裸机部署（CentOS/Ubuntu）

```bash
# 1. 装 Python 3.11 + 依赖
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. 配置环境变量（同 .env.example，建议写进 systemd 或 .env 并由 gunicorn 读取）
export DATABASE_URL="mysql+pymysql://user:pwd@127.0.0.1:3306/lvguanjia?charset=utf8mb4"
export CORS_ORIGINS="https://api.your-domain.com"

# 3. 启动（生产用 gunicorn，勿用 uvicorn 单进程）
gunicorn main:app -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000 -w 4

# 4. 初始化数据
python seed.py
```

再用 **nginx** 做反向代理 + HTTPS（配置见 `server/nginx.conf`）：
- 复制 `nginx.conf` 到 `/etc/nginx/conf.d/lvguanjia.conf`，改域名与证书路径；
- `nginx -t && systemctl reload nginx`。

### 方案 C：Serverless / 云托管（无需管服务器）

- **腾讯云 CloudBase 云托管 / 云函数**、**阿里云函数计算** 均支持 FastAPI（WSGI/ASGI）。
- 把 `server/` 作为服务代码，平台会自动用 `gunicorn` 拉起；数据库用同 VPC 的云数据库 MySQL。
- 平台通常自带 HTTPS 域名（需绑定你自己已备案的自定义域名给小程序用）。

### 方案 D：Cloud Studio 临时预览（仅演示，≠ 生产）

可用 `workbuddy_cloudstudio_deploy` 把静态产物部署预览，但**当前后端是 Python 服务、不是静态站点**，该方式跑不了 API，仅适合前端静态原型，不建议用于真实部署。

---

## 2. 数据库切换（生产建议 MySQL）

- 本地调试：`DATABASE_URL=sqlite:///./lvguanjia.db`（默认，零配置）。
- 生产：设 `DATABASE_URL` 为 MySQL 连接串（见 `.env.example`），代码已通过 `os.getenv` 读取，无需改代码。
- 首次启动 `Base.metadata.create_all` 会自动建表；演示数据用 `python seed.py` 灌入。
- 正式环境后续建议用 **Alembic** 做结构化迁移（当前为简化建表）。

---

## 3. 前端（小程序）发布

1. **换 AppID**：把 `miniprogram/project.config.json` 的 `appid` 改为你的真实 AppID。
2. **切真实后端**：编辑 `miniprogram/utils/config.js`
   ```js
   const useMock = false
   const BASE_URL = 'https://api.your-domain.com'   // 你的 HTTPS 域名
   ```
3. **配服务器域名**：微信公众平台 → 开发设置 → 服务器域名 →
   request 合法域名 增加 `https://api.your-domain.com`（upload/download/socket 按需）。
4. **上传代码**：微信开发者工具 → 上传 → 填版本号与备注。
5. **提交审核 → 发布**：审核通过后全量发布。
6. **类目与资质**：旅游类小程序需选择对应类目，并按需求说明书第 5 章准备
   《旅行社业务经营许可证》或合作资质、隐私政策页、ICP 备案（上线前置）。

> 体验阶段（不发布）也可保留 `useMock=true`，用测试号直接在开发者工具预览全部交互。

---

## 4. 生产安全清单（上线前逐条确认）

- [ ] `CORS_ORIGINS` 已设为真实域名，**删除 `"*"`**。
- [x] 管理员密码已用 **bcrypt** 哈希，登录签发 **JWT**，受保护接口均校验 `Authorization: Bearer <token>`（已实现）。**请务必更换默认密码 `admin/admin123`**。
- [x] 手机号等敏感字段**加密存储**（V1.3 已实现）：`server/utils/crypto.py` 用标准库（hashlib/base64/os，无第三方依赖）做 `enc:` 前缀可逆加密；写入全加密、接口返回自动解密；`server/migrate_phones.py` 可一次性把历史明文加密（幂等，可重复执行）。**管理后台界面已默认脱敏，点「显示」才暴露全号。**
- [x] 小程序用户端鉴权（V1.3 已实现）：`wx_login` 签发用户 JWT（30 天），收藏等接口改走 `get_current_user` 依赖，身份取自 token；管理员 token 加 `type:"admin"` 防越权。
- [x] 后台用户管理（V1.3 已实现）：`/api/users` 超管专属账号 CRUD（增删、改密码、改角色、启用/停用），禁止操作自身防锁死；`/api/admin/settings` 返回环境/安全状态（**绝不回显密钥明文**）。
- [ ] `seed.py` 中的演示数据在正式库清理或脱敏。
- [ ] HTTPS 证书有效且自动续期；`/docs` 已限制访问（nginx 配置已加 IP 白名单示例）。
- [ ] 微信小程序隐私政策页、用户协议已上线。
- [ ] 接入订阅消息（订单/成团提醒）、分享参数、微信支付（第二阶段）。

---

## 5. 部署后验证

```bash
# 后端健康检查
curl https://api.your-domain.com/

# 小程序侧：开发者工具「不校验合法域名」勾选后，先用 BASE_URL 指向测试环境联调；
# 正式联调需域名已备案并加入合法域名名单。
```

- 预期：下单 → 总额计算正确 → 确认定金状态流转 → 管理看板统计更新（与本地验证一致）。

---

## 6. 已生成的部署配套文件

| 文件 | 作用 |
| --- | --- |
| `server/Dockerfile` | 后端生产镜像（gunicorn + uvicorn worker） |
| `server/docker-compose.yml` | 后端 + MySQL 编排 |
| `server/.dockerignore` | 构建时忽略项 |
| `server/.env.example` | 生产环境变量模板 |
| `server/nginx.conf` | HTTPS 反向代理示例 |
| `deploy.bat` | Windows 一键：杀旧进程 + 构建前端 + 启动后端 + 手机号迁移 |
| `restart-backend.bat` | 轻量重启：仅杀旧进程 + 重启后端（不含前端构建，秒级修复 enc: 乱码） |
| `需求说明书_修订版V1.1.md` / `页面设计文档_V1.1.md` | 已升级至 **V1.3**（新增加密、用户JWT、用户管理/系统设置、我的资料/生日编辑） |
| `DEPLOY.md` | 本指南 |
