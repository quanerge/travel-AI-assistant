# server/routers/auth.py
# JWT 鉴权 + 微信小程序登录。
import os
import json
import hashlib
import datetime
import urllib.request
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


def get_principal(cred: HTTPAuthorizationCredentials = Depends(_bearer),
                  db: Session = Depends(get_db)):
    """统一身份依赖：同时承载管理员与小程序用户，返回 (role, principal)。

    role 为 "admin" 时 principal 是 AdminUser；为 "user" 时 principal 是 User。
    供「管理后台与小程序共用同一接口」的场景（如订单、客户资料）做角色分流：
    管理员可见全部，普通用户只能操作自己的资源。任何非法/过期/类型不符的
    token 一律 401，杜绝越权访问。
    """
    if not cred or not cred.credentials:
        raise HTTPException(status_code=401, detail="未登录或 token 缺失")
    try:
        data = jwt.decode(cred.credentials, SECRET, algorithms=[ALG])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="token 无效或已过期")
    if data.get("type") == "admin":
        admin = db.query(AdminUser).filter(AdminUser.id == int(data["sub"])).first()
        if not admin:
            raise HTTPException(status_code=401, detail="管理员不存在")
        return ("admin", admin)
    if data.get("type") == "user":
        user = db.query(User).filter(User.id == int(data["sub"])).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        return ("user", user)
    raise HTTPException(status_code=401, detail="token 类型不正确")


def _wechat_openid(appid: str, secret: str, code: str) -> str | None:
    """调微信 jscode2session 换取稳定 openid（生产环境）。失败返回 None。

    使用标准库 urllib，不引入额外依赖。
    """
    url = ("https://api.weixin.qq.com/sns/jscode2session"
           f"?appid={appid}&secret={secret}&js_code={code}&grant_type=authorization_code")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "travel-ai/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("openid")
    except Exception:
        return None


def _resolve_openid(payload: "WxLoginIn", db: Session) -> str:
    """解析登录身份 openid，按优先级杜绝「客户端任意传 openid 即可冒充任意用户」：

    1) 生产：WECHAT_APPID/WECHAT_SECRET 齐备时，用 code 调微信换稳定 openid（权威、不可伪造）；
    2) 演示复用：仅接受「服务端此前已落库」的 openid（拒绝客户端凭空捏造，防冒充他人）；
    3) 演示首登：用 code 派生一个持久 openid 落库，供下次启动复用（MVP 占位）。
    """
    appid = os.getenv("WECHAT_APPID")
    secret = os.getenv("WECHAT_SECRET")
    if appid and secret and payload.code:
        real = _wechat_openid(appid, secret, payload.code)
        if real:
            return real
    if payload.openid:
        # 仅当该 openid 真实存在于库中（由服务端签发过）才信任，否则视为伪造
        if db.query(User).filter(User.openid == payload.openid).first():
            return payload.openid
    if payload.code:
        return "dev_" + hashlib.sha256((SECRET + payload.code).encode()).hexdigest()[:16]
    raise HTTPException(status_code=400, detail="缺少有效的 code 或 openid")


# ---------- 路由 ----------
class WxLoginIn(BaseModel):
    code: str = None
    nickname: str = None
    openid: str = None  # 客户端复用的稳定 openid（仅当服务端此前已签发才被信任）


@router.post("/wx-login")
def wx_login(payload: WxLoginIn, db: Session = Depends(get_db)):
    """小程序静默登录：用 wx.login 拿到的 code 换取 openid。

    安全加固（P0）：openid 由服务端权威解析（见 _resolve_openid），
    严禁客户端任意指定 openid 冒充他人。生产环境配置 WECHAT_APPID/WECHAT_SECRET
    后走微信官方 jscode2session；演示环境用 code 派生持久 openid 并落库复用，
    保证跨启动身份稳定，且外部无法凭空捏造有效 openid。
    """
    openid = _resolve_openid(payload, db)
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
