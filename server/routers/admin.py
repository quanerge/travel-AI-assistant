# server/routers/admin.py
from datetime import datetime, timedelta
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import AdminUser, Order, Route, Customer
from schemas import AdminLogin, AdminLoginOut
from routers.auth import create_token, verify_password, migrate_password, get_current_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


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

    # 利润 = Σ(收入 - 成本)；收入取 total_amount，无则按 售价×人数 估算
    profit = 0.0
    for o in orders:
        if o.route_id and o.route_id in routes:
            r = routes[o.route_id]
            revenue = o.total_amount or (r.price * (o.person_count or 1))
            cost = (r.cost_price or 0) * (o.person_count or 1)
            profit += (revenue - cost)
    profit = round(profit, 2)

    week_ago = today - timedelta(days=7)
    customer_growth = db.query(Customer).filter(Customer.created_at >= week_ago).count()

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
    }
