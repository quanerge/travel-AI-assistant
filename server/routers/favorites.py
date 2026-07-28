# server/routers/favorites.py —— 用户收藏线路（需求 7.2 / 我的收藏）
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Favorite, Route
from routers.auth import get_current_user
from models import User

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


class FavoriteIn(BaseModel):
    route_id: int


@router.post("")
def toggle_favorite(payload: FavoriteIn,
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """收藏/取消收藏切换。返回 favorited 表示当前是否已收藏。

    需用户 JWT：identity 取自 token，避免越权操作他人收藏。
    """
    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id, Favorite.route_id == payload.route_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"favorited": False}
    f = Favorite(user_id=current_user.id, route_id=payload.route_id)
    db.add(f)
    db.commit()
    return {"favorited": True}


@router.get("")
def list_favorites(current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """返回当前用户收藏的线路列表（供「我的收藏」展示）。"""
    favs = db.query(Favorite).filter(Favorite.user_id == current_user.id).all()
    route_ids = [f.route_id for f in favs]
    if not route_ids:
        return []
    return db.query(Route).filter(Route.id.in_(route_ids)).all()
