# server/routers/orders.py
import time
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
from models import Order, Route, Payment
from schemas import OrderCreate, OrderOut
from routers.customers import upsert_customer_from_contact
from routers.auth import get_current_admin, get_current_user, get_principal
from utils.crypto import encrypt_phone
from utils.pagination import paginate, set_pagination_headers
from models import AdminUser, User

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _attach_route_name(db: Session, orders):
    """给订单对象批量挂上 route_name（按 route_id 一次查询映射，避免 N+1）。"""
    ids = {getattr(o, "route_id", None) for o in orders if getattr(o, "route_id", None)}
    if ids:
        mapping = {r.id: r.name for r in db.query(Route.id, Route.name).filter(Route.id.in_(ids)).all()}
        for o in orders:
            o.route_name = mapping.get(o.route_id)
    return orders


@router.post("", response_model=OrderOut)
def create_order(payload: OrderCreate, current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """小程序用户下单：身份以 JWT 为准，强制 user_id = 当前用户，杜绝伪造他人订单。"""
    payload.user_id = current_user.id
    order_no = "NO" + str(int(time.time() * 1000))
    total = None
    if payload.route_id:
        r = db.query(Route).filter(Route.id == payload.route_id).first()
        if r:
            total = r.price * payload.person_count
    order = Order(
        order_no=order_no,
        user_id=payload.user_id,
        route_id=payload.route_id,
        name=payload.name,
        phone=encrypt_phone(payload.phone),
        person_count=payload.person_count,
        departure_date=payload.departure_date,
        remark=payload.remark,
        status="pending_confirm",
        total_amount=total
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    # 归集客户：报名即客户，累加订单数与消费
    upsert_customer_from_contact(
        db, name=payload.name, phone=payload.phone,
        source="订单报名", order_count=1, order_amount=total or 0
    )
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(principal=Depends(get_principal), user_id: int = None,
                page: int = None, page_size: int = 50, response: Response = None,
                db: Session = Depends(get_db)):
    """订单列表：管理员可见全部（可按 user_id 筛选）；小程序用户仅可见自己的订单。"""
    role, obj = principal
    q = db.query(Order)
    if role == "user":
        q = q.filter(Order.user_id == obj.id)
    elif user_id:
        q = q.filter(Order.user_id == user_id)
    total, items = paginate(q.order_by(Order.id.desc()), page, page_size)
    set_pagination_headers(response, page, page_size, total)
    _attach_route_name(db, items)
    return items


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, principal=Depends(get_principal), db: Session = Depends(get_db)):
    role, obj = principal
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if role == "user" and o.user_id != obj.id:
        raise HTTPException(403, "无权查看该订单")
    _attach_route_name(db, [o])
    return o


@router.post("/{order_id}/confirm-deposit")
def confirm_deposit(order_id: int, admin: AdminUser = Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    """MVP 线下定金确认：顾问确认收款后订单推进。操作人强制取当前管理员。"""
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    o.status = "deposit_received"
    o.deposit_paid = True
    o.updated_at = None  # trigger onupdate
    db.add(Payment(order_id=o.id, type="deposit", amount=o.deposit_amount or 0,
                   method="offline", status="paid", operator_id=admin.id))
    db.commit()
    return {"status": o.status, "msg": "定金已确认"}


@router.post("/{order_id}/confirm")
def confirm_order(order_id: int, admin: AdminUser = Depends(get_current_admin),
                  db: Session = Depends(get_db)):
    """顾问确认订单：pending_confirm -> confirmed。"""
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if o.status != "pending_confirm":
        raise HTTPException(400, "仅「待确认」订单可确认")
    o.status = "confirmed"
    db.commit()
    return {"status": o.status, "msg": "订单已确认"}


@router.post("/{order_id}/complete")
def complete_order(order_id: int, admin: AdminUser = Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    """订单完成：流转到 completed（报名成功/已成团完成）。"""
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    o.status = "completed"
    db.commit()
    return {"status": o.status, "msg": "订单已完成"}
