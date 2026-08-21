# server/routers/routes.py
import json
import os
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session, joinedload
from database import get_db
from models import Route, RouteDay, RoutePoi, AdminUser
from schemas import RouteOut, RouteCreate, RouteUpdate, RouteDayCreate
from routers.auth import get_current_admin
from routers.ai import _build_highlight
from routers.upload import STATIC_DIR
from utils.llm import generate_poi_intro
from utils.tts import synthesize
from utils.pagination import paginate, set_pagination_headers

router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.get("", response_model=list[RouteOut])
def list_routes(category: str = None, keyword: str = None,
                min_days: int = None, max_days: int = None,
                departure: str = None, price_min: float = None, price_max: float = None,
                intensity: str = None,
                page: int = None, page_size: int = 50, response: Response = None,
                db: Session = Depends(get_db)):
    # 首页热门推荐/线路列表只展示可下单的自营线路（source='official'），
    # 网络推荐攻略（source='recommend'）走独立端点 /api/recommend-routes，不混入。
    q = db.query(Route).filter(Route.source != "recommend")
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
    route = (
        db.query(Route)
        .options(joinedload(Route.route_days).joinedload(RouteDay.pois))
        .filter(Route.id == route_id)
        .first()
    )
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


@router.post("/{route_id}/generate-poi", response_model=list)
def generate_poi(route_id: int, _admin=Depends(get_current_admin),
                db: Session = Depends(get_db)):
    """后台/系统触发：用 LLM 把该线路每天 route_day.content 拆成逐景点解说词。

    幂等 upsert（先删旧 pois 再批量插入），结果随线路详情接口 GET /api/routes/{id} 返回，
    供小程序逐景点语音播报。每条 intro 已由 LLM 控制在 ≤50 字以适配微信同声传译插件。
    """
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(404, "线路不存在")
    result = []
    for day in route.route_days:
        db.query(RoutePoi).filter(RoutePoi.route_day_id == day.id).delete()
        intros = generate_poi_intro(route.name, day.title, day.content or "")
        for i, p in enumerate(intros):
            db.add(RoutePoi(route_day_id=day.id, seq=i, name=p["name"], intro=p["intro"]))
            result.append({"day_no": day.day_no, "name": p["name"], "intro": p["intro"]})
    db.commit()
    return result


@router.get("/{route_id}/pois/{poi_id}/audio")
def get_poi_audio(route_id: int, poi_id: int, db: Session = Depends(get_db)):
    """公开端点（小程序用，无需登录）：返回某景点解说词音频的相对 URL。

    首次访问：用 TTS 把 poi.intro 合成为 mp3 落盘到 server/static/audio/{poi_id}.mp3 并缓存；
    后续访问：文件已存在直接返回（幂等、可刷新）。
    无 TTS 密钥 / 合成失败 / intro 为空时返回 404（前端据此禁用 🔊 按钮）。
    替代路线 B：原同声传译插件方案因小程序未备案无法添加，故改用后端预生成 mp3。
    """
    poi = db.query(RoutePoi).filter(RoutePoi.id == poi_id).first()
    if not poi:
        raise HTTPException(404, "景点不存在")
    # 归属校验：poi 必须属于该 route（经 route_day 关联），防越权/错配
    day = db.query(RouteDay).filter(RouteDay.id == poi.route_day_id).first()
    if not day or day.route_id != route_id:
        raise HTTPException(404, "景点不属于该线路")
    if not poi.intro or not poi.intro.strip():
        raise HTTPException(404, "该景点暂无语音解说词")
    audio_dir = os.path.join(STATIC_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(audio_dir, f"{poi_id}.mp3")
    if not os.path.exists(audio_path):
        mp3 = synthesize(poi.intro)
        if not mp3:
            raise HTTPException(404, "语音合成暂不可用（未配置 TTS 密钥或网络异常）")
        with open(audio_path, "wb") as f:
            f.write(mp3)
    return {"audio_url": f"/static/audio/{poi_id}.mp3"}
