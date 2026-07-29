# server/routers/users.py —— 后台用户管理（管理员账号 CRUD，仅超管可操作）
import bcrypt
import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import AdminUser
from routers.auth import get_current_admin
from utils.crypto import encrypt_phone, decrypt_phone
from utils.pagination import paginate, set_pagination_headers

router = APIRouter(prefix="/api/admin/users", tags=["admin-users"])

# 角色选项（与 AdminUser.role 一致）
ROLES = ("advisor", "super")


def require_super(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """仅超管可访问：非超管返回 403。"""
    if admin.role != "super":
        raise HTTPException(status_code=403, detail="仅超级管理员可管理用户")
    return admin


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "advisor"          # advisor / super
    phone: str = None


class PasswordReset(BaseModel):
    password: str


class RoleUpdate(BaseModel):
    role: str


class StatusUpdate(BaseModel):
    status: str                    # active / disabled


@router.get("")
def list_users(admin: AdminUser = Depends(require_super), db: Session = Depends(get_db),
              page: int = None, page_size: int = 50, response: Response = None):
    """列出全部管理员账号（不含密码）。"""
    total, rows = paginate(db.query(AdminUser).order_by(AdminUser.id), page, page_size)
    set_pagination_headers(response, page, page_size, total)
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "phone": decrypt_phone(u.phone),
            "status": getattr(u, "status", "active") or "active",
            "created_at": u.created_at,
        }
        for u in rows
    ]


@router.post("")
def create_user(payload: UserCreate, admin: AdminUser = Depends(require_super),
                db: Session = Depends(get_db)):
    """新建管理员账号（超管专属）。"""
    if db.query(AdminUser).filter(AdminUser.username == payload.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="角色非法")
    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    user = AdminUser(
        username=payload.username,
        password_hash=bcrypt.hashpw(payload.password.encode("utf-8"),
                                     bcrypt.gensalt()).decode("utf-8"),
        role=payload.role,
        phone=encrypt_phone(payload.phone),
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "role": user.role,
            "phone": decrypt_phone(user.phone), "status": "active"}


@router.put("/{user_id}/password")
def reset_password(user_id: int, payload: PasswordReset,
                   admin: AdminUser = Depends(require_super),
                   db: Session = Depends(get_db)):
    """重置某账号密码（超管专属）。"""
    u = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="账号不存在")
    if not payload.password or len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    u.password_hash = bcrypt.hashpw(payload.password.encode("utf-8"),
                                    bcrypt.gensalt()).decode("utf-8")
    db.commit()
    return {"msg": "密码已重置"}


@router.put("/{user_id}/role")
def change_role(user_id: int, payload: RoleUpdate,
                admin: AdminUser = Depends(require_super),
                db: Session = Depends(get_db)):
    """变更角色（超管专属）。禁止变更自己的角色，避免误操作锁死。"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能变更自身角色")
    u = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="账号不存在")
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="角色非法")
    u.role = payload.role
    db.commit()
    return {"msg": "角色已更新", "role": u.role}


@router.put("/{user_id}/status")
def change_status(user_id: int, payload: StatusUpdate,
                  admin: AdminUser = Depends(require_super),
                  db: Session = Depends(get_db)):
    """启用/停用账号（超管专属）。禁止停用自己。"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能停用当前登录账号")
    u = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="账号不存在")
    if payload.status not in ("active", "disabled"):
        raise HTTPException(status_code=400, detail="状态非法")
    u.status = payload.status
    db.commit()
    return {"msg": "状态已更新", "status": u.status}


@router.delete("/{user_id}")
def delete_user(user_id: int, admin: AdminUser = Depends(require_super),
                db: Session = Depends(get_db)):
    """删除账号（超管专属）。禁止删除自己。"""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录账号")
    u = db.query(AdminUser).filter(AdminUser.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="账号不存在")
    db.delete(u)
    db.commit()
    return {"msg": "已删除"}
