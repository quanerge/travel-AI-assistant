# server/routers/orders.py
import time
import re
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database import get_db, migrate
from models import Order, Route, Payment, Coupon
from schemas import OrderCreate, OrderOut
from routers.customers import upsert_customer_from_contact
from routers.auth import get_current_admin, get_current_user, get_principal
from utils.crypto import encrypt_phone
from utils.pagination import paginate, set_pagination_headers
from utils.wechat import send_subscribe_message
from models import AdminUser, User

logger = logging.getLogger("lvguanjia.orders")

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _attach_route_name(db: Session, orders):
    """给订单对象批量挂上 route_name（按 route_id 一次查询映射，避免 N+1）。"""
    ids = {getattr(o, "route_id", None) for o in orders if getattr(o, "route_id", None)}
    if ids:
        mapping = {r.id: r.name for r in db.query(Route.id, Route.name).filter(Route.id.in_(ids)).all()}
        for o in orders:
            o.route_name = mapping.get(o.route_id)
    return orders


def _push_pre_trip(db: Session, order):
    """定金确认（行程锁定）后，向用户推送行前提醒订阅消息（thing1/name2/time3）。
    失败（未授权/未配置）静默降级，不影响主流程。"""
    try:
        u = db.query(User).filter(User.id == order.user_id).first()
        if not u or not u.openid:
            return
        route_name = ""
        if order.route_id:
            r = db.query(Route).filter(Route.id == order.route_id).first()
            route_name = r.name if r else ""
        data = {
            "thing1": {"value": (route_name or "您的旅行行程")[:20]},
            "name2": {"value": "专属旅游顾问"},
            "time3": {"value": (order.departure_date or datetime.utcnow().strftime("%Y-%m-%d"))[:20]},
        }
        send_subscribe_message(
            u.openid, data,
            page="pages/orderDetail/orderDetail?id=" + str(order.id)
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("行前提醒推送异常: %s", e)


def _push_settled(db: Session, order):
    """尾款结清后，向用户推送「尾款已收·行程锁定」订阅消息（thing1/name2/time3）。
    失败（未授权/未配置）静默降级，不影响主流程。"""
    try:
        u = db.query(User).filter(User.id == order.user_id).first()
        if not u or not u.openid:
            return
        route_name = ""
        if order.route_id:
            r = db.query(Route).filter(Route.id == order.route_id).first()
            route_name = r.name if r else ""
        data = {
            "thing1": {"value": ("尾款已收·" + (route_name or "行程锁定"))[:20]},
            "name2": {"value": "专属旅游顾问"},
            "time3": {"value": (order.departure_date or datetime.utcnow().strftime("%Y-%m-%d"))[:20]},
        }
        send_subscribe_message(
            u.openid, data,
            page="pages/orderDetail/orderDetail?id=" + str(order.id)
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("尾款结清推送异常: %s", e)


@router.post("", response_model=OrderOut)
def create_order(payload: OrderCreate, current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """小程序用户下单：身份以 JWT 为准，强制 user_id = 当前用户，杜绝伪造他人订单。"""
    payload.user_id = current_user.id
    order_no = "NO" + str(int(time.time() * 1000))
    r = None
    total = None
    if payload.route_id:
        r = db.query(Route).filter(Route.id == payload.route_id).first()
        if r:
            total = r.price * payload.person_count
    # 定金按应收 30% 预估（MVP 固定 30%，后续可在线路/系统配置比例）
    deposit_amount = round((total or 0) * 0.3, 2)
    # 成本快照：下单时固化线路成本，保证历史利润可回溯（后续改线路价不影响已下单利润）
    cost_snapshot = (r.cost_price * payload.person_count) if (r and r.cost_price) else None
    # ---------- 优惠券抵扣（服务端校验，杜绝伪造优惠）----------
    coupon = None
    discount = 0
    if payload.coupon_id:
        coupon = db.query(Coupon).filter(
            Coupon.id == payload.coupon_id,
            Coupon.user_id == current_user.id,
            Coupon.status == "unused",
        ).first()
        if not coupon:
            raise HTTPException(400, "优惠券不可用或已被使用")
        if coupon.expire_at and coupon.expire_at < datetime.utcnow():
            raise HTTPException(400, "优惠券已过期")
        if coupon.applicable and coupon.applicable.startswith("route:"):
            rid = int(coupon.applicable.split(":", 1)[1])
            if payload.route_id != rid:
                raise HTTPException(400, "该优惠券仅限指定线路使用")
        elif coupon.applicable and coupon.applicable.startswith("category:"):
            need = coupon.applicable.split(":", 1)[1]
            if payload.route_id:
                r2 = db.query(Route).filter(Route.id == payload.route_id).first()
                if not (r2 and r2.category == need):
                    raise HTTPException(400, "该优惠券不适用此线路分类")
            else:
                raise HTTPException(400, "该优惠券需选择对应分类线路")
        if coupon.condition:
            m = re.search(r"(\d+(?:\.\d+)?)", coupon.condition)
            if m and total is not None and total < float(m.group(1)):
                raise HTTPException(400, "未满足优惠券使用门槛：" + coupon.condition)
        discount = coupon.amount or 0
        if total is not None:
            total = max(0, total - discount)
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
        total_amount=total,
        coupon_id=coupon.id if coupon else None,
        discount_amount=discount,
        deposit_amount=deposit_amount,
        cost_snapshot=cost_snapshot,
        # 应收尾款 = 最终总额 - 定金（定金已按原价 30% 预估，余额即尾款）；定金即全款时为 0
        balance_amount=round(max(0, (total or 0) - (deposit_amount or 0)), 2),
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    # 核销优惠券：下单成功后立即把所选券翻为 used，防止重复使用（先落库再归集客户，
    # 即便后续客户归集异常，订单与券核销已生效）
    if coupon:
        coupon.status = "used"
        db.commit()
    # 归集客户：报名即客户，累加订单数与消费
    upsert_customer_from_contact(
        db, name=payload.name, phone=payload.phone,
        source="订单报名", order_count=1, order_amount=total or 0
    )
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(principal=Depends(get_principal), user_id: int = None, status: str = None,
                page: int = None, page_size: int = 50, response: Response = None,
                db: Session = Depends(get_db)):
    """订单列表：管理员可见全部（可按 user_id / status 筛选）；小程序用户仅可见自己的订单。"""
    role, obj = principal
    q = db.query(Order)
    if role == "user":
        q = q.filter(Order.user_id == obj.id)
    elif user_id:
        q = q.filter(Order.user_id == user_id)
    if status:
        q = q.filter(Order.status == status)
    q = q.filter(or_(Order.is_deleted == False, Order.is_deleted.is_(None)))
    total, items = paginate(q.order_by(Order.id.desc()), page, page_size)
    set_pagination_headers(response, page, page_size, total)
    _attach_route_name(db, items)
    return items


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, principal=Depends(get_principal), db: Session = Depends(get_db)):
    role, obj = principal
    o = db.query(Order).filter(
        Order.id == order_id,
        or_(Order.is_deleted == False, Order.is_deleted.is_(None))
    ).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if role == "user" and o.user_id != obj.id:
        raise HTTPException(403, "无权查看该订单")
    _attach_route_name(db, [o])
    return o


@router.post("/{order_id}/confirm-deposit")
def confirm_deposit(order_id: int, admin: AdminUser = Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    """MVP 线下定金确认：顾问确认收款后订单推进。操作人强制取当前管理员。

    状态分支：
    - 仍有尾款（balance_amount > 0）→ 进入「待付尾款」(balance_pending)，等待顾问收尾款；
    - 定金即全款（balance_amount == 0）→ 直接结清 (completed)，尾款视为已收。
    """
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    o.deposit_paid = True
    bal = o.balance_amount if o.balance_amount is not None else max(0, round((o.total_amount or 0) - (o.deposit_amount or 0), 2))
    if bal > 0:
        o.status = "balance_pending"
        msg = "定金已确认，进入待付尾款"
    else:
        o.status = "completed"
        o.balance_paid = True
        o.settled_at = datetime.utcnow()
        msg = "定金已确认，定金即全款，订单已结清"
    db.add(Payment(order_id=o.id, type="deposit", amount=o.deposit_amount or 0,
                   method="offline", status="paid", operator_id=admin.id))
    db.commit()
    # 行程锁定：向用户推送行前提醒（订阅消息，需用户在小程序端授权）
    _push_pre_trip(db, o)
    return {"status": o.status, "msg": msg}


@router.post("/{order_id}/confirm-balance")
def confirm_balance(order_id: int, admin: AdminUser = Depends(get_current_admin),
                    db: Session = Depends(get_db)):
    """MVP 线下尾款确认：顾问确认收款后订单结清。操作人强制取当前管理员。

    要求订单处于「定金已收(deposit_received)/待付尾款(balance_pending)」且尾款未收。
    写一条 Payment(type=balance) 流水，置 balance_paid/settled_at，订单流转到 completed。
    """
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if o.balance_paid:
        raise HTTPException(400, "尾款已收，无需重复确认")
    if o.status not in ("deposit_received", "balance_pending"):
        raise HTTPException(400, "仅「定金已收/待付尾款」订单可收尾款")
    bal = o.balance_amount if o.balance_amount is not None else max(0, round((o.total_amount or 0) - (o.deposit_amount or 0), 2))
    o.balance_paid = True
    o.settled_at = datetime.utcnow()
    o.status = "completed"
    db.add(Payment(order_id=o.id, type="balance", amount=bal,
                   method="offline", status="paid", operator_id=admin.id))
    db.commit()
    _push_settled(db, o)
    return {"status": o.status, "msg": "尾款已确认，订单已结清"}


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
    """订单完成：流转到 completed（已成团完成）。

    防呆：尚有未收尾款时禁止直接标记完成，避免财务/履约记录悬空，
    必须先走 confirm-balance 收尾款（尾款为 0 的订单由 confirm-deposit 自动结清）。
    """
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if not o.balance_paid and (o.balance_amount or 0) > 0:
        raise HTTPException(400, "尚有尾款未收，请先确认尾款")
    o.status = "completed"
    db.commit()
    return {"status": o.status, "msg": "订单已完成"}


@router.post("/{order_id}/delete", response_model=OrderOut)
def delete_order(order_id: int, db: Session = Depends(get_db),
                 principal: tuple = Depends(get_principal)):
    """软删除订单（管理员与下单客户本人均可）。

    权限：
    - 管理员：可删除任意订单（清理测试 / 异常单）。
    - 客户：只能删除「自己」且「尚未产生资金往来」的订单（status 为待确认/待付定金，
      且未付定金）；已确认、已收定金或已完成的订单不允许自助删除，
      避免财务/履约记录悬空，需联系顾问处理。
    软删除仅置 is_deleted 标记，保留审计与支付记录，误删可恢复。
    """
    role, actor = principal
    o = db.query(Order).filter(Order.id == order_id).first()
    if not o:
        raise HTTPException(404, "订单不存在")
    if role == "user":
        if o.user_id != actor.id:
            raise HTTPException(403, "只能删除自己的订单")
        if o.deposit_paid or o.status in ("confirmed", "deposit_received", "success", "completed"):
            raise HTTPException(400, "该订单已确认/已付定金，无法直接删除，如需处理请联系顾问")
    o.is_deleted = True
    o.deleted_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        # 兜底：运行中的库可能尚未 migrate() 补齐软删除列，自动补列后重试一次（先回滚）
        db.rollback()
        migrate()
        db.commit()
    db.refresh(o)
    _attach_route_name(db, [o])
    return o
