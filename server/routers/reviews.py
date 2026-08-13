# server/routers/reviews.py —— 线路评价晒图（功能①）
import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Review, Route, User
from routers.auth import get_current_user
from schemas import ReviewIn, ReviewOut

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


def _serialize(r: Review, db: Session) -> dict:
    """评价脱敏序列化：仅暴露昵称/头像，绝不返回手机号。"""
    u = db.query(User).filter(User.id == r.user_id).first()
    nickname = u.nickname if (u and u.nickname) else "匿名用户"
    avatar = u.avatar if u else None
    imgs: List[str] = []
    if r.images:
        try:
            imgs = json.loads(r.images)
        except (ValueError, TypeError):
            imgs = []
    return {
        "id": r.id,
        "user_id": r.user_id,
        "route_id": r.route_id,
        "rating": r.rating,
        "content": r.content,
        "images": imgs,
        "status": r.status,
        "nickname": nickname,
        "avatar": avatar,
        "created_at": r.created_at,
    }


@router.get("")
def list_reviews(
    route_id: int = Query(..., description="线路 id"),
    page: int = 1,
    size: int = 10,
    db: Session = Depends(get_db),
):
    """公开：某线路的已通过评价列表 + 均分 + 总数。供详情页展示。"""
    if page < 1:
        page = 1
    if size < 1 or size > 50:
        size = 10
    base = db.query(Review).filter(Review.route_id == route_id, Review.status == "approved")
    total = base.count()
    avg = db.query(func.avg(Review.rating)).filter(
        Review.route_id == route_id, Review.status == "approved"
    ).scalar()
    items = (
        base.order_by(Review.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "total": total,
        "avg_rating": round(avg, 1) if avg else 0.0,
        "page": page,
        "size": size,
        "items": [_serialize(r, db) for r in items],
    }


@router.post("")
def create_review(
    payload: ReviewIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """登录态提交评价（评分 + 文字 + 晒图）。反向更新线路均分。"""
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="评分需在 1-5 之间")
    if not db.query(Route).filter(Route.id == payload.route_id).first():
        raise HTTPException(status_code=404, detail="线路不存在")
    r = Review(
        user_id=current_user.id,
        route_id=payload.route_id,
        rating=payload.rating,
        content=payload.content,
        images=json.dumps(payload.images or []),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    # 反向更新线路 rating 为已通过评价的均分，供详情页展示
    avg = db.query(func.avg(Review.rating)).filter(
        Review.route_id == payload.route_id, Review.status == "approved"
    ).scalar()
    if avg is not None:
        route = db.query(Route).filter(Route.id == payload.route_id).first()
        route.rating = round(avg, 1)
        db.commit()
    return _serialize(r, db)


@router.get("/mine")
def my_reviews(
    page: int = 1,
    size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """登录态：当前用户提交的全部评价（含待审）。"""
    if page < 1:
        page = 1
    if size < 1 or size > 50:
        size = 10
    base = db.query(Review).filter(Review.user_id == current_user.id)
    total = base.count()
    items = (
        base.order_by(Review.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "size": size,
        "items": [_serialize(r, db) for r in items],
    }
