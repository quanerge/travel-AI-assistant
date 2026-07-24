# server/routers/customers.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Customer, FollowUp, User
from schemas import (
    CustomerOut, CustomerCreate, CustomerUpdate,
    FollowUpOut, FollowUpCreate, CustomerRegister, RegisterOut
)

router = APIRouter(prefix="/api/customers", tags=["customers"])


def upsert_customer_from_contact(db: Session, name: str = None, phone: str = None,
                                 source: str = None, order_count: int = 0,
                                 order_amount: float = 0.0) -> Customer | None:
    """客户归集：订单/咨询产生时调用。

    匹配优先级：phone > name。命中则累加订单数/消费、刷新最后联系时间；
    未命中则新建。无联系方式（phone 与 name 都空）则不归集，返回 None。
    """
    if not phone and not name:
        return None

    cust = None
    if phone:
        cust = db.query(Customer).filter(Customer.phone == phone).first()
    if not cust and name:
        cust = db.query(Customer).filter(Customer.name == name).first()

    now = datetime.utcnow()
    if cust:
        cust.last_contact_at = now
        if source:
            cust.source = source
        if order_count:
            cust.total_orders = (cust.total_orders or 0) + order_count
            cust.follow_status = "deal"          # 已成单
        if order_amount:
            cust.total_amount = float(cust.total_amount or 0) + order_amount
    else:
        cust = Customer(
            name=name or "未知客户",
            phone=phone,
            source=source,
            total_orders=order_count,
            total_amount=order_amount,
            last_contact_at=now,
            follow_status="deal" if order_count else "pending_follow"
        )
        db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@router.get("", response_model=list[CustomerOut])
def list_customers(tag: str = None, follow_status: str = None, db: Session = Depends(get_db)):
    q = db.query(Customer)
    if tag:
        q = q.filter(Customer.tags.contains(tag))
    if follow_status:
        q = q.filter(Customer.follow_status == follow_status)
    return q.order_by(Customer.id.desc()).all()


@router.post("", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    """后台手动录入客户。"""
    cust = Customer(**payload.model_dump())
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@router.post("/register", response_model=RegisterOut)
def register_customer(payload: CustomerRegister, db: Session = Depends(get_db)):
    """小程序客户自助注册：创建 User + 关联 Customer（CRM 归集）。

    按手机号去重：已存在客户直接返回（幂等），避免重复建档。
    """
    import re
    if not re.match(r"^1\d{10}$", payload.phone or ""):
        raise HTTPException(400, "手机号格式不正确")

    existing = db.query(Customer).filter(Customer.phone == payload.phone).first()
    if existing:
        return RegisterOut(
            user_id=existing.user_id or 0,
            customer_id=existing.id,
            nickname=existing.name,
            phone=existing.phone,
            already_registered=True,
        )

    user = User(nickname=payload.nickname, phone=payload.phone, status="active")
    db.add(user)
    db.commit()
    db.refresh(user)

    cust = Customer(
        user_id=user.id,
        name=payload.nickname,
        phone=payload.phone,
        wechat_no=payload.wechat_no,
        source="miniprogram",
        travel_preference=payload.travel_preference,
        budget_range=payload.budget_range,
        follow_status="pending_follow",
    )
    db.add(cust)
    db.commit()
    db.refresh(cust)

    return RegisterOut(
        user_id=user.id,
        customer_id=cust.id,
        nickname=user.nickname,
        phone=user.phone,
        already_registered=False,
    )


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    """编辑客户资料（标签 / 备注 / 跟进状态 / 画像等）。"""
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(404, "客户不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cust, k, v)
    db.commit()
    db.refresh(cust)
    return cust


@router.get("/{customer_id}/follow-ups", response_model=list[FollowUpOut])
def list_follow_ups(customer_id: int, db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(404, "客户不存在")
    return db.query(FollowUp).filter(FollowUp.customer_id == customer_id).order_by(FollowUp.id.desc()).all()


@router.post("/{customer_id}/follow-ups", response_model=FollowUpOut)
def add_follow_up(customer_id: int, payload: FollowUpCreate, db: Session = Depends(get_db)):
    """添加一条跟进记录，并刷新客户最后联系时间。"""
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(404, "客户不存在")
    fu = FollowUp(customer_id=customer_id, content=payload.content)
    cust.last_contact_at = datetime.utcnow()
    if cust.follow_status == "pending_follow":
        cust.follow_status = "contacting"
    db.add(fu)
    db.commit()
    db.refresh(fu)
    return fu
