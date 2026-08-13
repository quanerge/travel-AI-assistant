# server/main.py
import os
import time
import logging
from collections import defaultdict, deque
from dotenv import load_dotenv

load_dotenv()  # 加载 .env（LLM_API_KEY / CORS_ORIGINS / WECHAT_CALLBACK_TOKEN 等），须在其它模块读 env 前执行


from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from database import engine, Base, migrate
import models  # noqa: ensure models registered
from routers import routes, orders, consult, customers, admin, upload, banners, favorites, auth, users, chat, ai, coupons, config, members

# 应用版本（可通过环境变量 APP_VERSION 覆盖，便于灰度/环境标记；默认与需求说明书 V1.3 对齐）
APP_VERSION = os.getenv("APP_VERSION", "V1.3")

# 创建表（演示用；生产请用 Alembic 迁移）
Base.metadata.create_all(bind=engine)
migrate()  # 为已存在表补齐新列（CRM 功能需要）

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lvguanjia")

app = FastAPI(title="旅途管家 API", version=APP_VERSION)

# ---------- CORS（安全收紧）----------
# 规则：明确白名单优于 "*"。当配置为 "*" 时不带 credentials（浏览器本就不允许
# 通配源携带凭据）；配置具体源时允许凭据，并显式暴露分页响应头。
raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
if raw_origins.strip() == "*":
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Page-Size"],
)

# ---------- 登录限流（防爆破）----------
# 针对 /api/auth/login 与 /api/auth/wx-login 做按 IP 的滑动窗口限流，
# 纯标准库实现，无第三方依赖。默认：60 秒内同一 IP 最多 10 次。
login_limiter = {"times": 10, "seconds": 60, "hits": defaultdict(deque)}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _login_allowed(ip: str) -> bool:
    cfg = login_limiter
    now = time.time()
    dq = cfg["hits"][ip]
    while dq and dq[0] <= now - cfg["seconds"]:
        dq.popleft()
    if len(dq) >= cfg["times"]:
        return False
    dq.append(now)
    return True


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.endswith("/api/auth/login") or path.endswith("/api/auth/wx-login"):
        ip = _client_ip(request)
        if not _login_allowed(ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "登录尝试过于频繁，请 60 秒后再试"},
                headers={"Retry-After": "60"},
            )
    return await call_next(request)


# ---------- 全局异常处理（不泄露堆栈）----------
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请稍后重试"})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "请求参数校验失败", "errors": exc.errors()},
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    logger.warning("DB integrity error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=409, content={"detail": "数据冲突（可能为唯一约束重复）"})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/api/version")
def api_version():
    """公开接口：返回当前后端应用版本，供管理后台左侧展示版本号。"""
    return {"version": APP_VERSION}


app.include_router(routes.router)
app.include_router(orders.router)
app.include_router(consult.router)
app.include_router(customers.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(banners.router)
app.include_router(favorites.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(ai.router)  # AI 行程自动规划（第二阶段）
app.include_router(coupons.router)  # 优惠券（领取 / 我的券 / 后台管理）
app.include_router(config.router)    # 站点公开配置（顾问联系方式等）
app.include_router(members.router)    # 会员体系（激活 member 表）

# 本地上传的静态资源（封面图等）：/static/covers/xxx.jpg
os.makedirs(upload.STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=upload.STATIC_DIR), name="static")

# 生产/本地一体：若已构建前端（admin/dist 存在），由后端直接托管，
# 访问 /ui/ 即可打开管理后台，与 /api 同源、无跨域/代理问题。
# 前端用 createWebHashHistory + base:'./'，挂子路径也能正常加载资源。
_ADMIN_DIST = os.path.join(os.path.dirname(__file__), "..", "admin", "dist")
if os.path.isdir(_ADMIN_DIST):
    app.mount("/ui", StaticFiles(directory=_ADMIN_DIST, html=True), name="admin-ui")


@app.get("/")
def root():
    # 已构建前端则跳转到后台界面，否则返回 API 信息
    if os.path.isdir(_ADMIN_DIST):
        return RedirectResponse("/ui/")
    return {"msg": "旅途管家 API", "docs": "/docs"}
