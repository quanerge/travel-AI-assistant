# server/routers/banners.py —— 首页 Banner 轮播配置（需求 7.1）
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from database import get_db
from models import Banner, AdminUser
from schemas import BannerOut, BannerCreate, BannerUpdate
from routers.auth import get_current_admin
from utils.pagination import paginate, set_pagination_headers

router = APIRouter(prefix="/api/banners", tags=["banners"])


@router.get("")
def list_banners(db: Session = Depends(get_db)):
    """前端首页调用：仅返回启用中的 Banner，按 sort 升序。"""
    return db.query(Banner).filter(Banner.status == "active").order_by(Banner.sort).all()


# ---------- 后台管理（需鉴权） ----------
@router.get("/admin", response_model=list[BannerOut])
def list_banners_admin(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db),
                      page: int = None, page_size: int = 50, response: Response = None):
    total, items = paginate(db.query(Banner).order_by(Banner.sort), page, page_size)
    set_pagination_headers(response, page, page_size, total)
    return items


@router.post("/admin", response_model=BannerOut, status_code=201)
def create_banner(payload: BannerCreate, admin: AdminUser = Depends(get_current_admin),
                  db: Session = Depends(get_db)):
    b = Banner(**payload.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.put("/admin/{bid}", response_model=BannerOut)
def update_banner(bid: int, payload: BannerUpdate, admin: AdminUser = Depends(get_current_admin),
                  db: Session = Depends(get_db)):
    b = db.query(Banner).filter(Banner.id == bid).first()
    if not b:
        raise HTTPException(404, "Banner 不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(b, k, v)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/admin/{bid}")
def delete_banner(bid: int, admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    b = db.query(Banner).filter(Banner.id == bid).first()
    if not b:
        raise HTTPException(404, "Banner 不存在")
    db.delete(b)
    db.commit()
    return {"ok": True, "id": bid}
