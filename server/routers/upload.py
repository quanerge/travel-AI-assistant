# server/routers/upload.py
# 封面图等本地图片上传：保存到 server/static/covers/，并返回可被 Web/小程序访问的相对 URL。
import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter(prefix="/api/upload", tags=["upload"])

# server/static —— 后端对外提供静态资源的根目录（需在 main.py 中挂载 StaticFiles）
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
COVER_DIR = os.path.join(STATIC_DIR, "covers")

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/cover")
async def upload_cover(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "仅支持 jpg / png / webp / gif 图片")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "图片不能超过 5MB")
    os.makedirs(COVER_DIR, exist_ok=True)
    name = uuid.uuid4().hex + ext
    with open(os.path.join(COVER_DIR, name), "wb") as f:
        f.write(content)
    # 返回相对路径，前端按自身域名/后端地址拼接即可（小程序侧会自动补后端前缀）
    return {"url": f"/static/covers/{name}"}
