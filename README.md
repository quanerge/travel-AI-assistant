# 旅途管家 · MVP 代码包

> 对应文档：`需求说明书_修订版V1.1.md`、`页面设计文档_V1.1.md`
> 范围：微信小程序（用户端 MVP）+ FastAPI 后端（含演示数据）
> 说明：本包实现 V1.0 MVP 必做项；在线支付、分销、AI 自动规划、会员体系按文档第二阶段实现（已预留接口/入口）。

## 目录结构

```
旅游AI小助手/
├── miniprogram/              微信小程序前端（用户端 MVP）
│   ├── app.js / app.json / app.wxss
│   ├── project.config.json / sitemap.json
│   ├── utils/                config / request / mock / api
│   └── pages/                9 个页面（首页/线路/详情/规划/报名/订单/订单详情/我的/咨询）
├── server/                   FastAPI 后端
│   ├── main.py               应用入口（CORS + 路由）
│   ├── database.py           引擎/会话（SQLite 默认，可切 MySQL）
│   ├── models.py             11 张表（对应需求 9 章）
│   ├── schemas.py            Pydantic 模型
│   ├── routers/              routes / orders / consult / customers / admin
│   ├── seed.py               演示数据（3 线路 + 管理员）
│   └── requirements.txt
├── 需求说明书_修订版V1.1.md
├── 页面设计文档_V1.1.md
└── README.md
```

## 一、小程序运行方式

1. 用 **微信开发者工具** 导入 `miniprogram/` 目录（AppID 可用测试号）。
2. 默认 `utils/config.js` 中 `useMock = true`，**无需后端即可预览全部页面与交互**（数据来自 `utils/mock.js`）。
3. 联调后端时，把 `useMock` 改为 `false` 并设置 `BASE_URL` 为你部署的后端地址（小程序需在后台配置合法域名）。

## 二、后端运行方式

```bash
cd server
# 1) 安装依赖（已用隔离环境验证，建议复用）
pip install -r requirements.txt

# 2) 初始化演示数据（生成 lvguanjia.db）
python seed.py

# 3) 启动服务
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

- 接口文档：http://127.0.0.1:8000/docs
- 默认管理员：`admin / admin123`（演示用明文哈希，生产务必换 bcrypt/argon2）

### 切换 MySQL（生产）
设置环境变量 `DATABASE_URL`：
```
DATABASE_URL="mysql+pymysql://user:pwd@host:3306/lvguanjia?charset=utf8mb4"
```
代码已通过 `os.getenv` 读取，无需改代码。

## 三、已验证接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/routes` | 线路列表 |
| GET | `/api/routes/{id}` | 线路详情（含行程） |
| POST | `/api/orders` | 报名下单（自动算总额） |
| GET | `/api/orders` | 订单列表（可 `?user_id=`） |
| POST | `/api/orders/{id}/confirm-deposit` | MVP 线下定金确认 |
| POST | `/api/consult` | 智能需求单 / 留言 |
| GET | `/api/customers` | CRM 客户列表（管理端） |
| POST | `/api/admin/login` | 管理员登录 |
| GET | `/api/admin/dashboard` | 管理后台看板 |

> 已实测：下单 → 总额计算（3999×2=7998）→ 确认定金状态流转 → 看板统计更新，均正常。

## 四、已知待补项

- **图标资源**：`tabBar` 与线路封面当前用文字/色块占位，需补充 PNG 图标与真实图片。
- **登录**：小程序 `app.js` 的 `wx.login` 仅占位，需联后端换取 `openid` 并落 `user` 表。
- **安全**：手机号加密、密码哈希、接口鉴权（JWT）按文档第 5、10 章补充。
- **管理后台 Web**：当前仅有 API，前端管理界面按 `页面设计文档` 第 6 章可基于 Vue/React 搭建。
- **微信生态**：订阅消息（订单/成团提醒）、分享卡片参数、微信支付（二阶段）待接入。
- **合规**：旅行社资质 / ICP 备案 / 隐私政策页为上线前置项（见需求第 5 章）。

## 五、下一步建议

1. 小程序导入后先以 `useMock=true` 走通主流程（浏览→详情→报名→订单）。
2. 启动后端，改为 `useMock=false` 验证真实接口。
3. 补图标、登录、鉴权、管理后台 Web，进入第二阶段（AI 规划 / 会员 / 拼团 / 支付）。
