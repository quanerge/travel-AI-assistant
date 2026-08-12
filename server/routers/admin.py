# server/routers/admin.py
import os
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db, DATABASE_URL
from models import AdminUser, Order, Route, Customer
from schemas import AdminLogin, AdminLoginOut
from routers.auth import create_token, verify_password, migrate_password, get_current_admin
from routers.customers import birthday_match
from utils.crypto import decrypt_phone

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _parse_dt(s, is_end=False):
    """将 YYYY-MM-DD 或 ISO 时间字符串解析为 datetime；is_end 时日期默认取到当日 23:59:59.999999。"""
    if not s:
        return None
    s = s.strip()
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = datetime.fromisoformat(s + "T00:00:00")
    if is_end and len(s) == 10:
        dt = datetime.fromisoformat(s + "T23:59:59.999999")
    return dt


def _compute_revenue(db: Session, start=None, end=None):
    """统一收益口径：Dashboard 与「收益管理」共用，确保两页一致。

    规则：
    - 排除软删除订单
    - 收入 revenue = total_amount（已含优惠券抵扣）；为 None 时回退 售价×人数
    - 成本 cost = 下单时快照 cost_snapshot；无快照(历史单)回退 当前线路成本×人数；再无则 0
    - 利润 = revenue - cost
    - 已收定金 = 窗口内 deposit_paid 订单的 deposit_amount 之和
    - start/end 按 created_at 过滤（含端点当日）
    """
    q = db.query(Order).filter(or_(Order.is_deleted == False, Order.is_deleted.is_(None)))
    if start:
        q = q.filter(Order.created_at >= start)
    if end:
        q = q.filter(Order.created_at <= end)
    orders = q.order_by(Order.id.desc()).all()
    routes = {r.id: r for r in db.query(Route).all()}

    total_income = 0.0
    total_profit = 0.0
    deposit_income = 0.0
    deposit_paid_orders = 0
    details = []
    for o in orders:
        r = routes.get(o.route_id) if o.route_id else None
        revenue = o.total_amount if o.total_amount is not None else (r.price * (o.person_count or 1) if r else 0)
        if o.cost_snapshot is not None:
            cost = o.cost_snapshot
            cost_unset = False
        elif r and r.cost_price:
            cost = r.cost_price * (o.person_count or 1)
            cost_unset = False
        else:
            cost = 0.0
            cost_unset = True
        profit = revenue - cost
        if o.deposit_paid:
            deposit_income += (o.deposit_amount or 0)
            deposit_paid_orders += 1
        total_income += revenue
        total_profit += profit
        details.append({
            "id": o.id,
            "order_no": o.order_no,
            "name": o.name,
            "route_id": o.route_id,
            "route_name": r.name if r else None,
            "person_count": o.person_count,
            "total_amount": round(revenue, 2),
            "discount_amount": round(o.discount_amount or 0, 2),
            "cost": round(cost, 2),
            "cost_unset": cost_unset,
            "profit": round(profit, 2),
            "status": o.status,
            "deposit_paid": bool(o.deposit_paid),
            "created_at": o.created_at,
        })
    return {
        "total_income": round(total_income, 2),
        "total_profit": round(total_profit, 2),
        "deposit_income": round(deposit_income, 2),
        "deposit_paid_orders": deposit_paid_orders,
        "details": details,
    }


@router.get("/revenue")
def revenue(start: str = None, end: str = None,
            admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """收益管理统一口径（与 Dashboard 累计利润一致）。start/end：YYYY-MM-DD 或 ISO 时间。"""
    start_dt = _parse_dt(start, is_end=False)
    end_dt = _parse_dt(end, is_end=True)
    return _compute_revenue(db, start_dt, end_dt)


@router.post("/login", response_model=AdminLoginOut)
def login(payload: AdminLogin, db: Session = Depends(get_db)):
    admin = db.query(AdminUser).filter(AdminUser.username == payload.username).first()
    if not admin or not verify_password(admin.password_hash, payload.password):
        raise HTTPException(status_code=401, detail="账号或密码错误")
    # 历史明文哈希首次登录成功后就地升级为 bcrypt
    migrate_password(admin, payload.password, db)
    return AdminLoginOut(
        token=create_token(admin.id, admin.role),
        id=admin.id,
        username=admin.username,
        role=admin.role,
    )


@router.get("/dashboard")
def dashboard(admin: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """管理后台看板：今日订单 / 本月收入 / 利润 / 客户增长 / 热门线路 TOP5 / 近30天趋势 / 待办。"""
    today = datetime.utcnow().date()
    orders = db.query(Order).all()
    routes = {r.id: r for r in db.query(Route).all()}

    today_orders = sum(1 for o in orders if o.created_at and o.created_at.date() == today)

    month_income = sum(
        (o.total_amount or 0) for o in orders
        if o.created_at and o.created_at.year == today.year and o.created_at.month == today.month
    )

    # 累计利润与「收益管理」页统一口径（含软删除过滤、无线路单、优惠抵0 等）
    profit = round(_compute_revenue(db)["total_profit"], 2)

    # 未软删除的客户过滤条件（历史数据 is_deleted 可能为 NULL，需一并视为未删除）
    alive_customer = or_(Customer.is_deleted == False, Customer.is_deleted.is_(None))  # noqa: E712

    week_ago = today - timedelta(days=7)
    customer_growth = (
        db.query(Customer)
        .filter(Customer.created_at >= week_ago)
        .filter(alive_customer)
        .count()
    )

    top_routes = (
        db.query(Route).filter(Route.status == "active")
        .order_by(Route.signup_count.desc()).limit(5).all()
    )
    top5 = [{"id": r.id, "name": r.name, "signup_count": r.signup_count, "price": r.price}
            for r in top_routes]

    trend = defaultdict(int)
    for o in orders:
        if o.created_at:
            d = o.created_at.date()
            if (today - d).days <= 30:
                trend[d.isoformat()] += 1
    trend_list = [{"date": k, "count": trend[k]} for k in sorted(trend.keys())]

    pending_confirm = db.query(Order).filter(Order.status == "pending_confirm").count()
    pending_deposit = db.query(Order).filter(Order.status == "pending_deposit").count()

    # 生日/纪念日提醒：今天 + 明天过生日的客户（offset 0=今天, 1=明天）
    # 必须排除已软删除客户，否则点击提醒跳转 CRM 后该客户不在默认列表里，看上去"跳过去什么都没有"
    birthday_reminders = []
    for c in (db.query(Customer)
                .filter(Customer.birthday.isnot(None))
                .filter(Customer.birthday != "")
                .filter(alive_customer).all()):
        off = birthday_match(c.birthday, today, 1)
        if off is not None:
            birthday_reminders.append({
                "customer_id": c.id,
                "name": c.name,
                "phone": decrypt_phone(c.phone),
                "wechat_no": c.wechat_no,
                "birthday": c.birthday,
                "offset": off,
                "order_count": c.total_orders or 0,
                "total_spent": round(c.total_amount or 0, 2),
            })
    birthday_reminders.sort(key=lambda x: x["offset"])

    return {
        "today_orders": today_orders,
        "month_income": round(month_income, 2),
        "profit": profit,
        "customer_growth": customer_growth,
        "active_routes": len([r for r in routes.values() if r.status == "active"]),
        "top_routes": top5,
        "order_trend": trend_list,
        "pending_confirm_orders": pending_confirm,
        "pending_deposit_orders": pending_deposit,
        "birthday_reminders": birthday_reminders,
    }


@router.get("/settings")
def settings(admin: AdminUser = Depends(get_current_admin)):
    """系统设置：返回环境/安全配置状态，供后台「系统设置」页展示。

    仅返回布尔/摘要，绝不回显密钥明文。
    """
    jwt_secret = os.getenv("JWT_SECRET", "")
    phone_key = os.getenv("PHONE_ENCRYPT_KEY", "")
    raw_origins = os.getenv("CORS_ORIGINS", "*")
    return {
        "version": "1.3",
        "db_type": "mysql" if DATABASE_URL.startswith("mysql") else "sqlite",
        "jwt_secret_configured": bool(jwt_secret) and jwt_secret != "lvguanjia-dev-secret",
        "phone_key_configured": bool(phone_key) and phone_key != "lvguanjia-dev-phone-secret-change-me",
        "cors_policy": "开放(*)" if raw_origins == "*" else "受限白名单",
        "current_role": admin.role,
    }
