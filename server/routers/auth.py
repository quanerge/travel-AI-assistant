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
from models import AdminUser, User, Customer
from utils.crypto import decrypt_phone

router = APIRouter(prefix="/api/auth", tags=["auth"])

SECRET = os.getenv("JWT_SECRET", "lvguanjia-dev-secret")
ALG = "HS256"
TOKEN_EXPIRE_HOURS = 12                # 管理员 token 有效期
USER_TOKEN_EXPIRE_DAYS = 30            # 小程序用户 token 有效期（移动端保持长期登录）

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
        "type": "admin",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET, algorithm=ALG)


def create_user_token(user_id: int) -> str:
    """签发小程序用户 token（type=user，长期有效）。"""
    payload = {
        "sub": str(user_id),
        "type": "user",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=USER_TOKEN_EXPIRE_DAYS),
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
    if data.get("type") != "admin":
        raise HTTPException(status_code=401, detail="token 类型不正确")
    admin = db.query(AdminUser).filter(AdminUser.id == int(data["sub"])).first()
    if not admin:
        raise HTTPException(status_code=401, detail="管理员不存在")
    return admin


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(_bearer),
                     db: Session = Depends(get_db)) -> User:
    """小程序用户鉴权依赖：从 Authorization: Bearer <token> 解析当前用户。

    用户接口必须带此依赖，确保只能操作自己的资源（收藏等）。
    用户 token 与管理员 token 通过 payload.type 区分，互不可越权。
    """
    if not cred or not cred.credentials:
        raise HTTPException(status_code=401, detail="未登录或 token 缺失")
    try:
        data = jwt.decode(cred.credentials, SECRET, algorithms=[ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    if data.get("type") != "user":
        raise HTTPException(status_code=401, detail="非用户 token")
    user = db.query(User).filter(User.id == int(data["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


# ---------- 路由 ----------
class WxLoginIn(BaseModel):
    code: str = None
    nickname: str = None
    openid: str = None  # 客户端复用的稳定 openid（首次由 code 派生后存本地），优先于 code


@router.post("/wx-login")
def wx_login(payload: WxLoginIn, db: Session = Depends(get_db)):
    """小程序静默登录：用 wx.login 拿到的 code 换取 openid。

    MVP 说明：真实环境应拿 code 调微信 jscode2session 换 openid+session_key；
    这里以 code 直接作为 openid 兜底（演示可用），上线时替换为微信接口返回。

    若客户端已持有上次登录派生的 openid（存本地复用），优先用 openid 定位用户，
    保证跨启动身份稳定。找到用户后顺带查出其注册客户，返回 customer 信息，
    供前端在退出后重新打开时自动恢复登录态，无需再次注册。
    """
    openid = payload.openid or payload.code
    if not openid:
        raise HTTPException(status_code=400, detail="缺少 code 或 openid")
    # TODO(上线): openid = wechat_jscode2session(code)["openid"]
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(openid=openid, nickname=payload.nickname or "微信用户", status="active")
        db.add(user)
        db.commit()
        db.refresh(user)

    # 关联客户：若此微信用户已完成小程序注册，返回客户信息以支持自动恢复登录
    result = {"user_id": user.id, "openid": user.openid, "token": create_user_token(user.id)}
    cust = db.query(Customer).filter(Customer.user_id == user.id).first()
    if cust:
        result["customer_id"] = cust.id
        result["nickname"] = cust.name
        result["phone"] = decrypt_phone(cust.phone)
        result["birthday"] = cust.birthday
        result["wechat_no"] = cust.wechat_no
    return result


@router.get("/me")
def me(admin: AdminUser = Depends(get_current_admin)):
    """返回当前登录的管理员信息（前端刷新页面时校验 token 用）。"""
    return {"id": admin.id, "username": admin.username, "role": admin.role}
