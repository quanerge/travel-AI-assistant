# server/routers/consult.py
import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session
from database import get_db, migrate
from models import ConsultRecord, User, Route, Customer, Order
from schemas import ConsultCreate, ConsultOut, ConsultUpdate, ConsultToOrder, OrderOut
from routers.auth import get_current_admin, get_current_user, get_principal
from routers.customers import upsert_customer_from_contact
from utils.crypto import encrypt_phone, decrypt_phone
from utils.wechat import send_subscribe_message
from utils.pagination import paginate, set_pagination_headers

router = APIRouter(prefix="/api/consult", tags=["consult"])


def _attach_route_name(db: Session, records):
    """给咨询记录批量挂上 route_name（按 route_id 一次查询映射，避免 N+1）。"""
    ids = {getattr(r, "route_id", None) for r in records if getattr(r, "route_id", None)}
    if ids:
        mapping = {r.id: r.name for r in db.query(Route.id, Route.name).filter(Route.id.in_(ids)).all()}
        for r in records:
            r.route_name = mapping.get(r.route_id)
    return records


def _attach_customer_identity(db: Session, records):
    """咨询记录自身缺姓名/手机时，回退到关联客户(优先)/用户身份，确保顾问能看到归属人。

    仅补充缺失项，绝不覆盖已填写的姓名/手机。Customer/User 的手机为 enc: 加密存储，
    由 ConsultOut.phone 的 validator 统一解密。
    """
    need = [r for r in records if (not r.name or not r.phone) and r.user_id]
    if not need:
        return records
    uids = {r.user_id for r in need}
    cust_map = {c.user_id: c for c in db.query(Customer).filter(Customer.user_id.in_(uids)).all()}
    user_map = {u.id: u for u in db.query(User).filter(User.id.in_(uids)).all()}
    for r in need:
        cust = cust_map.get(r.user_id)
        if not r.name:
            u = user_map.get(r.user_id)
            r.name = (cust.name if cust and cust.name else (u.nickname if u and u.nickname else None))
        if not r.phone:
            u = user_map.get(r.user_id)
            r.phone = (cust.phone if cust and cust.phone else (u.phone if u and u.phone else None))
    return records


@router.post("", response_model=ConsultOut)
def create_consult(payload: ConsultCreate, current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """咨询/智能需求单提交（MVP：plan 通道由顾问人工回执）。

    身份以 JWT 为准，强制 user_id = 当前用户，杜绝冒名提交/篡改归属。
    """
    payload.user_id = current_user.id
    rec = ConsultRecord(
        user_id=payload.user_id,
        channel=payload.channel,
        name=payload.name,
        phone=encrypt_phone(payload.phone),
        content=payload.content,
        route_id=payload.route_id
    )
    db.add(rec)
    try:
        db.commit()
    except Exception:
        # 兜底：库尚未 migrate() 补齐新列时自动补列后重试
        migrate()
        db.commit()
    db.refresh(rec)
    # 归集客户：留言即潜在客户（按姓名/手机匹配，无订单不累加消费）
    try:
        upsert_customer_from_contact(db, name=payload.name, phone=payload.phone, source=payload.channel)
    except Exception:
        pass
    return rec


@router.get("", response_model=list[ConsultOut])
def list_consult(_admin=Depends(get_current_admin), db: Session = Depends(get_db),
                page: int = None, page_size: int = 50, response: Response = None):
    """咨询列表含客户手机号等 PII，仅管理员可读。软删除记录不展示。"""
    total, items = paginate(
        db.query(ConsultRecord).filter(
            or_(ConsultRecord.is_deleted == False, ConsultRecord.is_deleted.is_(None))
        ).order_by(ConsultRecord.id.desc()), page, page_size
    )
    set_pagination_headers(response, page, page_size, total)
    _attach_route_name(db, items)
    _attach_customer_identity(db, items)
    return items


@router.get("/mine", response_model=list[ConsultOut])
def my_consults(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """小程序用户查看自己的咨询/需求单及顾问回复（身份以 JWT 为准，仅看自己的；软删除不展示）。"""
    items = db.query(ConsultRecord).filter(
        ConsultRecord.user_id == user.id,
        or_(ConsultRecord.is_deleted == False, ConsultRecord.is_deleted.is_(None))
    ).order_by(ConsultRecord.id.desc()).all()
    _attach_route_name(db, items)
    _attach_customer_identity(db, items)
    return items


@router.get("/unread-count")
def consult_unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户有多少条「顾问已回复、但自己尚未查看」的咨询（用于未读红点）。"""
    n = db.query(ConsultRecord).filter(
        ConsultRecord.user_id == user.id,
        or_(ConsultRecord.is_deleted == False, ConsultRecord.is_deleted.is_(None)),
        ConsultRecord.reply_at.isnot(None),
        or_(ConsultRecord.customer_read_at.is_(None), ConsultRecord.customer_read_at < ConsultRecord.reply_at),
    ).count()
    return {"count": n}


@router.put("/{consult_id}", response_model=ConsultOut)
def update_consult(consult_id: int, payload: ConsultUpdate,
                   _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    """顾问人工回执：填写方案/回复、上传附件、编辑行程卡片、更新处理状态、指派处理人（仅管理员）。

    写入 reply_content 即视为「已回复」：自动记录 reply_at / reply_by，
    且若当前为待处理则流转为 replied（方案已出待客户确认）。
    回复成功后会尝试通过微信订阅消息通知客户（配置齐全且客户已授权才送达，否则静默跳过）。
    """
    rec = db.query(ConsultRecord).filter(ConsultRecord.id == consult_id).first()
    if not rec:
        raise HTTPException(404, "咨询记录不存在")
    if payload.status is not None:
        rec.status = payload.status
    if payload.handled_by is not None:
        rec.handled_by = payload.handled_by
    if payload.reply_content is not None:
        rec.reply_content = payload.reply_content
        rec.reply_at = datetime.utcnow()
        rec.reply_by = _admin.id
        if rec.status == "pending":
            rec.status = "replied"
    if payload.attachments is not None:
        rec.attachments = payload.attachments
    if payload.itinerary is not None:
        rec.itinerary = payload.itinerary
    try:
        db.commit()
    except Exception:
        # 兜底：运行中的库可能尚未执行 migrate() 补齐 P3 新增列（attachments/itinerary），
        # 自动补列后重试一次，避免「服务器内部错误」。
        migrate()
        db.commit()
    db.refresh(rec)
    # 以下为返回体富化（挂线路名/补客户身份/推订阅消息），任一环节异常都不应阻断已保存的方案
    try:
        _attach_route_name(db, [rec])
        _attach_customer_identity(db, [rec])
    except Exception:
        pass
    if payload.reply_content is not None and rec.user_id:
        try:
            _push_subscribe_if_possible(db, rec, advisor_name=_admin.username)
        except Exception:
            pass
    return rec


def _push_subscribe_if_possible(db: Session, rec: ConsultRecord, advisor_name: str = ""):
    """回复后尝试推送订阅消息；缺配置/未授权时静默跳过。"""
    u = db.query(User).filter(User.id == rec.user_id).first()
    if not u or not u.openid:
        return
    data = {
        "thing1": {"value": (rec.route_name or "您的专属旅行方案")[:20]},
        "name2": {"value": (advisor_name or "旅行顾问")[:10]},
        "time3": {"value": (rec.reply_at or datetime.utcnow()).strftime("%Y-%m-%d %H:%M")},
    }
    send_subscribe_message(u.openid, data)


@router.post("/{consult_id}/to-order", response_model=OrderOut)
def consult_to_order(consult_id: int, payload: ConsultToOrder,
                     user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """小程序「对此方案下单」：把需求单（含顾问方案）一键转为正式订单（仅本人）。

    姓名/手机/线路取自该需求单（缺省时回退到关联客户/用户身份）；
    生成待确认订单并归集客户，同时把需求单标记为已处理(done)。
    """
    rec = db.query(ConsultRecord).filter(
        ConsultRecord.id == consult_id, ConsultRecord.user_id == user.id,
        or_(ConsultRecord.is_deleted == False, ConsultRecord.is_deleted.is_(None))
    ).first()
    if not rec:
        raise HTTPException(404, "咨询记录不存在")

    # 姓名/手机缺失时回退到关联客户/用户身份，保证下单信息完整
    _attach_customer_identity(db, [rec])
    name = rec.name
    phone = decrypt_phone(rec.phone)
    if not name or not phone:
        raise HTTPException(400, "需求单缺少联系人姓名/手机，无法下单，请补全后重试")

    route_id = rec.route_id
    person_count = payload.person_count or 1
    total = None
    if route_id:
        r = db.query(Route).filter(Route.id == route_id).first()
        if r:
            total = r.price * person_count

    order_no = "NO" + str(int(time.time() * 1000))
    order = Order(
        order_no=order_no,
        user_id=user.id,
        route_id=route_id,
        name=name,
        phone=encrypt_phone(phone),
        person_count=person_count,
        departure_date=payload.departure_date,
        remark=payload.remark or f"来自需求单 #{rec.id}",
        status="pending_confirm",
        total_amount=total,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 归集客户：需求单转订单视为一次报名
    upsert_customer_from_contact(
        db, name=name, phone=phone,
        source="需求单转订单", order_count=1, order_amount=total or 0
    )
    # 需求单闭环：标记为已处理
    rec.status = "done"
    db.commit()

    _attach_route_name(db, [order])
    return order


@router.post("/{consult_id}/read", response_model=ConsultOut)
def mark_consult_read(consult_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """客户查看方案后标记已读（仅本人），用于消除未读红点。"""
    rec = db.query(ConsultRecord).filter(
        ConsultRecord.id == consult_id, ConsultRecord.user_id == user.id
    ).first()
    if not rec:
        raise HTTPException(404, "咨询记录不存在")
    rec.customer_read_at = datetime.utcnow()
    db.commit()
    db.refresh(rec)
    _attach_route_name(db, [rec])
    _attach_customer_identity(db, [rec])
    return rec


@router.post("/{consult_id}/delete", response_model=ConsultOut)
def delete_consult(consult_id: int, db: Session = Depends(get_db),
                   principal: tuple = Depends(get_principal)):
    """软删除咨询/需求单（管理员与提交客户本人均可）。

    权限：
    - 管理员：可删除任意需求单（用于清理广告 / 测试数据）。
    - 客户：只能删除「自己」且「尚未转为订单」的需求单；已转订单(status=done)不允许删除，
      避免把已成交订单悬空。
    软删除仅置 is_deleted 标记，不物理删行，保留审计痕迹，误删可恢复。
    """
    role, actor = principal
    rec = db.query(ConsultRecord).filter(ConsultRecord.id == consult_id).first()
    if not rec:
        raise HTTPException(404, "咨询记录不存在")
    if role == "user":
        if rec.user_id != actor.id:
            raise HTTPException(403, "只能删除自己的咨询")
        if rec.status == "done":
            raise HTTPException(400, "该需求单已转为订单，无法直接删除，如需处理请联系顾问")
    rec.is_deleted = True
    rec.deleted_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        # 兜底：运行中的库可能尚未 migrate() 补齐软删除列，自动补列后重试一次
        migrate()
        db.commit()
    db.refresh(rec)
    _attach_route_name(db, [rec])
    _attach_customer_identity(db, [rec])
    return rec
