# server/routers/coupons.py —— 优惠券最小闭环
#
# 数据模型约定：用 Coupon 表同时承载「券模板」与「用户已领券」，
# 以 user_id 是否为空区分：
#   - user_id IS NULL  -> 券模板（后台创建，可公开领取），status: active/inactive
#   - user_id IS NOT NULL -> 用户已领取的券实例，status: unused/used/expired
# 模板用 code 作为批次标识；用户领取时复制一份继承模板金额/门槛/有效期/适用。
import re
import time
import random
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from models import Coupon
from schemas import CouponOut, CouponCreate, CouponUpdate
from routers.auth import get_current_admin, get_current_user
from utils.pagination import paginate, set_pagination_headers

router = APIRouter(prefix="/api/coupons", tags=["coupons"])


def _now():
    return datetime.utcnow()


def _is_expired(c: Coupon) -> bool:
    return c.expire_at is not None and c.expire_at < _now()


def _gen_batch_code() -> str:
    """生成模板批次码：CP + 时间戳后 8 位 + 4 位随机数字，保证唯一。"""
    return "CP" + str(int(time.time()))[-8:] + "".join(random.choices(string.digits, k=4))


# ---------------- 小程序端（需登录）----------------

@router.get("", response_model=list[CouponOut])
def list_claimable_coupons(db: Session = Depends(get_db)):
    """首页「领券中心」调用：返回可领取的券模板（user_id 为空、启用中、未过期）。"""
    rows = (
        db.query(Coupon)
        .filter(Coupon.user_id.is_(None), Coupon.status == "active")
        .order_by(Coupon.id.desc())
        .all()
    )
    return [r for r in rows if not _is_expired(r)]


@router.get("/mine", response_model=list[CouponOut])
def my_coupons(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """我的优惠券：按领取时间倒序；未使用但已过期的在展示态标记为 expired（不落库）。"""
    rows = db.query(Coupon).filter(Coupon.user_id == user.id).order_by(Coupon.id.desc()).all()
    for c in rows:
        if c.status == "unused" and _is_expired(c):
            c.status = "expired"
    return rows


@router.post("/{cid}/claim", response_model=CouponOut)
def claim_coupon(cid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """领取优惠券：把模板复制成当前用户的一张券实例。

    防重复领取：同批次(code)已领过且仍可用则直接返回已有券，避免重复堆券。
    """
    tpl = db.query(Coupon).filter(Coupon.id == cid, Coupon.user_id.is_(None)).first()
    if not tpl:
        raise HTTPException(404, "优惠券不存在或不可领取")
    if tpl.status != "active":
        raise HTTPException(400, "该优惠券已停止发放")
    if _is_expired(tpl):
        raise HTTPException(400, "该优惠券已过期")

    existing = (
        db.query(Coupon)
        .filter(Coupon.user_id == user.id, Coupon.code == tpl.code, Coupon.status == "unused")
        .first()
    )
    if existing:
        return existing

    newc = Coupon(
        code=tpl.code,
        title=tpl.title,
        user_id=user.id,
        amount=tpl.amount,
        condition=tpl.condition,
        applicable=tpl.applicable,
        expire_at=tpl.expire_at,
        status="unused",
    )
    db.add(newc)
    db.commit()
    db.refresh(newc)
    return newc


# ---------------- 管理后台（需管理员 token）----------------

@router.get("/admin", response_model=list[CouponOut])
def list_coupons_admin(_admin=Depends(get_current_admin), db: Session = Depends(get_db),
                       page: int = None, page_size: int = 50, response: Response = None):
    """优惠券后台列表（模板 + 已发放的用户券），按 id 倒序。模板 user_id 为空。"""
    total, items = paginate(db.query(Coupon).order_by(Coupon.id.desc()), page, page_size)
    set_pagination_headers(response, page, page_size, total)
    return items


@router.post("/admin", response_model=CouponOut, status_code=201)
def create_coupon(payload: CouponCreate, _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    """后台新建券模板（user_id 留空 = 可公开领取）。"""
    c = Coupon(
        code=_gen_batch_code(),
        title=payload.title,
        user_id=None,
        amount=payload.amount,
        condition=payload.condition,
        applicable=payload.applicable,
        expire_at=payload.expire_at,
        status=payload.status,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@router.put("/admin/{cid}", response_model=CouponOut)
def update_coupon(cid: int, payload: CouponUpdate, _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    c = db.query(Coupon).filter(Coupon.id == cid).first()
    if not c:
        raise HTTPException(404, "优惠券不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return c


@router.delete("/admin/{cid}")
def delete_coupon(cid: int, _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    c = db.query(Coupon).filter(Coupon.id == cid).first()
    if not c:
        raise HTTPException(404, "优惠券不存在")
    db.delete(c)
    db.commit()
    return {"ok": True, "id": cid}
