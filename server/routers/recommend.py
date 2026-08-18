# server/routers/recommend.py
"""线路亮点自动分发（顾问零操作闭环）。

流程：
1) 客户在小程序产生意向（收藏 / 咨询 / 下单）→ 系统自动 upsert 一条 RouteRecommend
   并预生成该线路的 AI 亮点（复用 ai._build_highlight，优先读线路缓存），即"自动发送给客户"。
2) 客户在「我的推荐」看到推给他的线路亮点，点「确认接受 / 暂不需要」。
3) 确认后状态回写为 accepted，顾问在后台「客户意向」视图零操作即可看到谁接受了。

绝不从小程序直连大模型：密钥安全 + 微信域名白名单 + CORS。
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import RouteRecommend, Route, User, Customer, AdminUser
from routers.auth import get_current_user, get_current_admin

router = APIRouter(prefix="/api/recommend", tags=["recommend"])


class RecommendIn(BaseModel):
    route_id: int = ...


def _ensure_highlight(route: Route, customer: Customer, db: Session) -> str | None:
    """复用线路亮点：优先读 route.ai_highlight 缓存，否则即时生成并写回缓存。

    返回 JSON 字符串（供 recommend.highlight_json 与小程序直接读取）。
    大模型不可用时返回 None，由客户端降级展示线路基础信息。
    """
    if route.ai_highlight:
        return route.ai_highlight
    try:
        # 延迟导入，避免任何潜在的模块循环依赖
        from routers.ai import _build_highlight
        h = _build_highlight(route, customer)
        s = __import__("json").dumps(h, ensure_ascii=False)
        route.ai_highlight = s
        db.add(route)
        db.commit()
        return s
    except Exception:  # noqa: BLE001
        db.rollback()
        return None


def _serialize(rec: RouteRecommend, route: Route | None, cust: Customer | None) -> dict:
    h = None
    if rec.highlight_json:
        try:
            h = __import__("json").loads(rec.highlight_json)
        except Exception:
            h = None
    return {
        "id": rec.id,
        "route_id": rec.route_id,
        "route_name": route.name if route else "—",
        "route_cover": route.cover if route else None,
        "route_days": route.days if route else None,
        "route_price": route.price if route else None,
        "route_destination": route.destination if route else None,
        "status": rec.status,
        "highlight": h,
        "created_at": rec.created_at,
        "accepted_at": rec.accepted_at,
    }


@router.post("")
def create_recommend(req: RecommendIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """客户侧自动分发入口：upsert 一条推荐并预生成亮点。

    幂等：同一用户对同一线路只保留一条（pending → 不重复创建）。
    顾问无需任何操作，客户一产生意向即被系统推送。
    """
    route = db.query(Route).filter(Route.id == req.route_id).first()
    if not route:
        raise HTTPException(404, "线路不存在")
    cust = db.query(Customer).filter(Customer.user_id == user.id).first()

    rec = db.query(RouteRecommend).filter(
        RouteRecommend.user_id == user.id,
        RouteRecommend.route_id == route.id,
    ).first()
    if not rec:
        rec = RouteRecommend(
            user_id=user.id,
            customer_id=cust.id if cust else None,
            route_id=route.id,
            status="pending",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

    # 预生成亮点（读缓存或即时生成写回），存到 recommend 供客户端直接读
    try:
        rec.highlight_json = _ensure_highlight(route, cust, db)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
    return _serialize(rec, route, cust)


@router.get("/mine")
def my_recommends(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前客户收到的所有推荐（按时间倒序）。"""
    recs = db.query(RouteRecommend).filter(
        RouteRecommend.user_id == user.id
    ).order_by(RouteRecommend.created_at.desc()).all()
    out = []
    for rec in recs:
        route = db.query(Route).filter(Route.id == rec.route_id).first()
        cust = db.query(Customer).filter(Customer.id == rec.customer_id).first() if rec.customer_id else None
        out.append(_serialize(rec, route, cust))
    return out


def _own_recommend(rec_id: int, user: User, db: Session) -> RouteRecommend:
    rec = db.query(RouteRecommend).filter(
        RouteRecommend.id == rec_id,
        RouteRecommend.user_id == user.id,
    ).first()
    if not rec:
        raise HTTPException(404, "推荐不存在")
    return rec


@router.post("/{rec_id}/accept")
def accept_recommend(rec_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """客户确认接受该线路推荐。状态回写 accepted，并记录接受时间。"""
    rec = _own_recommend(rec_id, user, db)
    rec.status = "accepted"
    rec.accepted_at = datetime.utcnow()
    rec.declined_at = None
    db.commit()
    return {"id": rec.id, "status": rec.status, "accepted_at": rec.accepted_at}


@router.post("/{rec_id}/decline")
def decline_recommend(rec_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """客户暂不需要该线路推荐。状态回写 declined。"""
    rec = _own_recommend(rec_id, user, db)
    rec.status = "declined"
    rec.declined_at = datetime.utcnow()
    rec.accepted_at = None
    db.commit()
    return {"id": rec.id, "status": rec.status, "declined_at": rec.declined_at}


@router.get("/admin")
def admin_recommends(status: str = None, db: Session = Depends(get_db),
                     _admin: AdminUser = Depends(get_current_admin)):
    """顾问视图：列出所有推荐（可按状态筛选），显示客户/线路/状态/时间。零操作。"""
    q = db.query(RouteRecommend)
    if status:
        q = q.filter(RouteRecommend.status == status)
    recs = q.order_by(RouteRecommend.created_at.desc()).all()
    out = []
    for rec in recs:
        route = db.query(Route).filter(Route.id == rec.route_id).first()
        cust = db.query(Customer).filter(Customer.id == rec.customer_id).first() if rec.customer_id else None
        user = db.query(User).filter(User.id == rec.user_id).first()
        name = (cust.name if cust else None) or (user.nickname if user else None) or ("用户#" + str(rec.user_id))
        out.append({
            "id": rec.id,
            "customer_id": rec.customer_id,
            "customer_name": name,
            "route_id": rec.route_id,
            "route_name": route.name if route else "—",
            "status": rec.status,
            "created_at": rec.created_at,
            "accepted_at": rec.accepted_at,
        })
    return out
