# server/routers/auth.py
# JWT 鉴权 + 微信小程序登录。
import os
import datetime
import bcrypt
import jwt

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import AdminUser, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET = os.getenv("JWT_SECRET", "lvguanjia-dev-secret")
ALG = "HS256"
TOKEN_EXPIRE_HOURS = 12

_bearer = HTTPBearer(auto_error=False)


# ---------- 密码校验（兼容历史明文哈希，首次登录自动迁移为 bcrypt） ----------
def _fake_hash(pwd: str) -> str:
    return "h:" + pwd


def verify_password(hash_str: str, pwd: str) -> bool:
    if not hash_str:
        return False
    if hash_str.startswith("h:"):
        # 历史演示库：明文前缀哈希，登录成功后就地升级为 bcrypt
        return hash_str == _fake_hash(pwd)
    try:
        return bcrypt.checkpw(pwd.encode("utf-8"), hash_str.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def migrate_password(admin: AdminUser, pwd: str, db: Session) -> None:
    """历史明文哈希首次校验通过后，改写为 bcrypt 存储。"""
    if admin.password_hash.startswith("h:"):
        admin.password_hash = bcrypt.hashpw(pwd.encode("utf-8"),
                                            bcrypt.gensalt()).decode("utf-8")
        db.commit()


# ---------- JWT ----------
def create_token(admin_id: int, role: str) -> str:
    payload = {
        "sub": str(admin_id),
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALG)


def get_current_admin(cred: HTTPAuthorizationCredentials = Depends(_bearer),
                      db: Session = Depends(get_db)) -> AdminUser:
    """受保护接口依赖：从 Authorization: Bearer <token> 解析当前管理员。"""
    if not cred or not cred.credentials:
        raise HTTPException(status_code=401, detail="未登录或 token 缺失")
    try:
        data = jwt.decode(cred.credentials, SECRET, algorithms=[ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    admin = db.query(AdminUser).filter(AdminUser.id == int(data["sub"])).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    return admin


# ---------- 路由 ----------
class WxLoginIn(BaseModel):
    code: str
    nickname: str = None


@router.post("/wx-login")
def wx_login(payload: WxLoginIn, db: Session = Depends(get_db)):
    """小程序静默登录：用 wx.login 拿到的 code 换取 openid。

    MVP 说明：真实环境应拿 code 调微信 jscode2session 换 openid+session_key；
    这里以 code 直接作为 openid 兜底（演示可用），上线时替换为微信接口返回。
    """
    if not payload.code:
        raise HTTPException(status_code=400, detail="缺少 code")
    openid = payload.code  # TODO(上线): openid = wechat_jscode2session(code)["openid"]
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(openid=openid, nickname=payload.nickname or "微信用户", status="active")
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"user_id": user.id, "openid": user.openid}


@router.get("/me")
def me(admin: AdminUser = Depends(get_current_admin)):
    """返回当前登录的管理员信息（前端刷新页面时校验 token 用）。"""
    return {"id": admin.id, "username": admin.username, "role": admin.role}
