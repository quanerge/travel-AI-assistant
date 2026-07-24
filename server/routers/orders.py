# server/routers/orders.py
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Order, Route, Payment
from schemas import OrderCreate, OrderOut
from routers.customers import upsert_customer_from_contact
from routers.auth import get_current_admin
from models import AdminUser

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
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
        phone=payload.phone,
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
def list_orders(user_id: int = None, db: Session = Depends(get_db)):
    q = db.query(Order)
    if user_id:
        q = q.filter(Order.user_id == user_id)
    return q.order_by(Order.id.desc()).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    return o


@router.post("/{order_id}/confirm-deposit")
def confirm_deposit(order_id: int, operator_id: int = None, db: Session = Depends(get_db)):
    """MVP 线下定金确认：顾问确认收款后订单推进。"""
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    o.status = "deposit_received"
    o.deposit_paid = True
    o.updated_at = None  # trigger onupdate
    db.add(Payment(order_id=o.id, type="deposit", amount=o.deposit_amount or 0,
                   method="offline", status="paid", operator_id=operator_id))
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
