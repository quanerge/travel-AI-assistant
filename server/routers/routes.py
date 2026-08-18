# server/routers/routes.py
import json
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
from models import Route, RouteDay, AdminUser
from schemas import RouteOut, RouteCreate, RouteUpdate, RouteDayCreate
from routers.auth import get_current_admin
from routers.ai import _build_highlight
from utils.pagination import paginate, set_pagination_headers

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.get("", response_model=list[RouteOut])
def list_routes(category: str = None, keyword: str = None,
                min_days: int = None, max_days: int = None,
                departure: str = None, price_min: float = None, price_max: float = None,
                intensity: str = None,
                page: int = None, page_size: int = 50, response: Response = None,
                db: Session = Depends(get_db)):
    q = db.query(Route)
    if category and category != "全部":
        q = q.filter(Route.category == category)
    if keyword:
        q = q.filter(Route.name.contains(keyword) | Route.destination.contains(keyword))
    if min_days is not None:
        q = q.filter(Route.days >= min_days)
    if max_days is not None:
        q = q.filter(Route.days <= max_days)
    if departure:
        q = q.filter(Route.departure.contains(departure))
    if price_min is not None:
        q = q.filter(Route.price >= price_min)
    if price_max is not None:
        q = q.filter(Route.price <= price_max)
    if intensity:
        q = q.filter(Route.intensity_level == intensity)
    total, items = paginate(q, page, page_size)
    set_pagination_headers(response, page, page_size, total)
    return items


@router.get("/{route_id}", response_model=RouteOut)
def get_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, "线路不存在")
    return route


@router.get("/{route_id}/highlight")
def get_route_highlight(route_id: int, db: Session = Depends(get_db)):
    """公开端点（小程序用，无需登录）：返回该线路的 AI 亮点解读。

    优先读线路缓存 ai_highlight（顾问在后台生成过则直接返回，零 LLM 调用）；
    无缓存时即时调用大模型生成并写回缓存，后续请求免费。生成失败自动降级兜底。
    返回：route_id / route_name / generated(是否本次新生成) / overview / must_see /
    food / scenery / tips / share_text / source / warning。
    """
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, "线路不存在")
    generated = False
    cached = route.ai_highlight
    if cached:
        try:
            h = json.loads(cached)
        except Exception:  # noqa: BLE001
            cached = None
    if not cached:
        h = _build_highlight(route)  # 通用版（不带客户个性化）
        try:
            route.ai_highlight = json.dumps(h, ensure_ascii=False)
            db.add(route)
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        generated = True
    return {
        "route_id": route.id,
        "route_name": route.name,
        "generated": generated,
        "overview": h.get("overview", ""),
        "must_see": h.get("must_see", []),
        "food": h.get("food", []),
        "scenery": h.get("scenery", []),
        "tips": h.get("tips", []),
        "share_text": h.get("share_text", ""),
        "source": h.get("source", "llm"),
        "warning": h.get("warning"),
    }


@router.post("", response_model=RouteOut, status_code=201)
def create_route(payload: RouteCreate, admin: AdminUser = Depends(get_current_admin),
                db: Session = Depends(get_db)):
    data = payload.model_dump(exclude={"route_days"})
    if data.get("gallery") is not None:
        data["gallery"] = json.dumps(data["gallery"], ensure_ascii=False)
    route = Route(**data, created_by=admin.id)
    if payload.route_days:
        route.route_days = [_day_model(d) for d in payload.route_days]
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


@router.put("/{route_id}", response_model=RouteOut)
def update_route(route_id: int, payload: RouteUpdate,
                _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, "线路不存在")
    updates = payload.model_dump(exclude_unset=True, exclude={"route_days"})
    if "gallery" in updates and updates["gallery"] is not None:
        updates["gallery"] = json.dumps(updates["gallery"], ensure_ascii=False)
    for k, v in updates.items():
        setattr(route, k, v)
    # 传了 route_days 则整体替换（cascade delete-orphan 自动删旧子表）
    if payload.route_days is not None:
        route.route_days = [_day_model(d) for d in payload.route_days]
    db.commit()
    db.refresh(route)
    return route


@router.delete("/{route_id}")
def delete_route(route_id: int, _admin=Depends(get_current_admin),
                db: Session = Depends(get_db)):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, "线路不存在")
    db.query(RouteDay).filter(RouteDay.route_id == route.id).delete()
    db.delete(route)
    db.commit()
    return {"ok": True, "id": route_id}


def _day_model(d: RouteDayCreate) -> RouteDay:
    return RouteDay(**d.model_dump())
