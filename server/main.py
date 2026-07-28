# server/main.py
import os

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import engine, Base, migrate
import models  # noqa: ensure models registered
from routers import routes, orders, consult, customers, admin, upload, banners, favorites, auth, users

# 创建表（演示用；生产请用 Alembic 迁移）
Base.metadata.create_all(bind=engine)
migrate()  # 为已存在表补齐新列（CRM 功能需要）

app = FastAPI(title="旅途管家 API", version="1.1")

raw_origins = os.getenv("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in raw_origins.split(",")] if raw_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# 本地上传的静态资源（封面图等）：/static/covers/xxx.jpg
os.makedirs(upload.STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=upload.STATIC_DIR), name="static")


@app.get("/")
def root():
    return {"msg": "旅途管家 API", "docs": "/docs"}
