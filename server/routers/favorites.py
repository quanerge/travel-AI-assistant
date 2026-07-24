# server/routers/favorites.py —— 用户收藏线路（需求 7.2 / 我的收藏）
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from models import Favorite, Route

router = APIRouter(prefix="/api/favorites", tags=["favorites"])


class FavoriteIn(BaseModel):
    user_id: int = None
    route_id: int


@router.post("")
def toggle_favorite(payload: FavoriteIn, db: Session = Depends(get_db)):
    """收藏/取消收藏切换。返回 favorited 表示当前是否已收藏。"""
    if not payload.user_id:
        raise HTTPException(status_code=400, detail="缺少 user_id")
    existing = db.query(Favorite).filter(
        Favorite.user_id == payload.user_id, Favorite.route_id == payload.route_id
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return {"favorited": False}
    f = Favorite(user_id=payload.user_id, route_id=payload.route_id)
    db.add(f)
    db.commit()
    return {"favorited": True}


@router.get("")
def list_favorites(user_id: int = None, db: Session = Depends(get_db)):
    """返回该用户收藏的线路列表（供「我的收藏」展示）。"""
    if not user_id:
        return []
    favs = db.query(Favorite).filter(Favorite.user_id == user_id).all()
    route_ids = [f.route_id for f in favs]
    if not route_ids:
        return []
    return db.query(Route).filter(Route.id.in_(route_ids)).all()
