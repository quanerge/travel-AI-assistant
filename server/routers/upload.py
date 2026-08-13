# server/routers/upload.py
# 封面图等本地图片上传：保存到 server/static/covers/，并返回可被 Web/小程序访问的相对 URL。
import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from routers.auth import get_current_admin, get_current_user
from models import User

router = APIRouter(prefix="/api/upload", tags=["upload"])

# server/static —— 后端对外提供静态资源的根目录（需在 main.py 中挂载 StaticFiles）
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
COVER_DIR = os.path.join(STATIC_DIR, "covers")
ATTACHMENT_DIR = os.path.join(STATIC_DIR, "attachments")
REVIEW_DIR = os.path.join(STATIC_DIR, "reviews")

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/cover")
async def upload_cover(file: UploadFile = File(...),
                      _admin=Depends(get_current_admin)):
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


@router.post("/file")
async def upload_file(file: UploadFile = File(...),
                     _admin=Depends(get_current_admin)):
    """顾问上传方案附件（图片）：保存到 server/static/attachments/，返回相对 URL。

    仅管理员可上传。附件以图片为主（行程单/报价单拍照等），便于小程序客户直接查看。
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "仅支持 jpg / png / webp / gif 图片")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "图片不能超过 5MB")
    os.makedirs(ATTACHMENT_DIR, exist_ok=True)
    name = uuid.uuid4().hex + ext
    with open(os.path.join(ATTACHMENT_DIR, name), "wb") as f:
        f.write(content)
    return {"url": f"/static/attachments/{name}"}


@router.post("/user-image")
async def upload_user_image(file: UploadFile = File(...),
                            current_user: User = Depends(get_current_user)):
    """小程序用户晒图上传（评价/我的足迹等）：保存到 server/static/reviews/，返回相对 URL。

    与封面/附件接口不同，此处用普通用户 JWT 鉴权（get_current_user），
    仅校验类型与大小，不暴露管理员权限。
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "仅支持 jpg / png / webp / gif 图片")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, "图片不能超过 5MB")
    os.makedirs(REVIEW_DIR, exist_ok=True)
    name = uuid.uuid4().hex + ext
    with open(os.path.join(REVIEW_DIR, name), "wb") as f:
        f.write(content)
    return {"url": f"/static/reviews/{name}"}
