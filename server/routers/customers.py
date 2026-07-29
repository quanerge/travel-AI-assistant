# server/routers/customers.py
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
from models import Customer, FollowUp, User
from schemas import (
    CustomerOut, CustomerCreate, CustomerUpdate,
    FollowUpOut, FollowUpCreate, CustomerRegister, RegisterOut
)
from utils.crypto import encrypt_phone, decrypt_phone
from utils.pagination import paginate, set_pagination_headers
from routers.auth import get_current_admin, get_principal

router = APIRouter(prefix="/api/customers", tags=["customers"])


def _auth_customer_writer(customer_id: int,
                          principal=Depends(get_principal),
                          db: Session = Depends(get_db)):
    """客户资料写入鉴权：管理员可改任意客户；小程序用户仅能改自己名下的客户资料。

    防止普通用户篡改他人 CRM 资料（越权写）。
    """
    role, obj = principal
    if role == "admin":
        return
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust or cust.user_id != obj.id:
        raise HTTPException(status_code=403, detail="无权操作该客户资料")
    return


def _validate_md(birthday: str) -> str | None:
    """校验生日格式 "MM-DD"，非法返回 None。"""
    import re
    if not birthday:
        return None
    m = re.match(r"^(\d{2})-(\d{2})$", birthday.strip())
    if not m:
        return None
    mm, dd = int(m.group(1)), int(m.group(2))
    if not (1 <= mm <= 12 and 1 <= dd <= 31):
        return None
    return f"{mm:02d}-{dd:02d}"


def birthday_match(birthday: str, today, days: int = 1):
    """返回生日落在 [今天, 今天+days] 内的偏移天数；不在范围内返回 None。

    birthday 存 "MM-DD"（去掉年份，纪念日只看月日）；today 为 date 对象。
    0=今天, 1=明天, 2=后天…
    """
    if not birthday or len(birthday) != 5:
        return None
    for i in range(days + 1):
        d = today + timedelta(days=i)
        if d.strftime("%m-%d") == birthday:
            return i
    return None


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
        cust = db.query(Customer).filter(Customer.phone == encrypt_phone(phone)).first()
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
            phone=encrypt_phone(phone),
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
def list_customers(tag: str = None, follow_status: str = None,
                   page: int = None, page_size: int = 50,
                   response: Response = None,
                   _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
    q = db.query(Customer)
    if tag:
        q = q.filter(Customer.tags.contains(tag))
    if follow_status:
        q = q.filter(Customer.follow_status == follow_status)
    total, items = paginate(q.order_by(Customer.id.desc()), page, page_size)
    set_pagination_headers(response, page, page_size, total)
    return items


@router.get("/birthdays")
def birthday_reminders(days: int = 1, _admin=Depends(get_current_admin),
                       db: Session = Depends(get_db)):
    """生日/纪念日提醒：返回生日为今天或未来 days 天内的客户。

    默认 days=1 -> 今天 + 明天。offset: 0=今天, 1=明天, 2=后天…
    用于管理后台在客户生日当天/前一天提醒顾问发送生日关怀。
    """
    if days < 0:
        days = 0
    today = datetime.utcnow().date()
    result = []
    for c in db.query(Customer).filter(Customer.birthday.isnot(None)).all():
        off = birthday_match(c.birthday, today, days)
        if off is not None:
            result.append({
                "customer_id": c.id,
                "name": c.name,
                "phone": decrypt_phone(c.phone),
                "wechat_no": c.wechat_no,
                "birthday": c.birthday,
                "offset": off,
            })
    # 按临近程度排序：今天优先
    result.sort(key=lambda x: x["offset"])
    return result


@router.post("", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, _admin=Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    """后台手动录入客户。"""
    data = payload.model_dump()
    data["phone"] = encrypt_phone(data.get("phone"))
    cust = Customer(**data)
    db.add(cust)
    db.commit()
    db.refresh(cust)
    return cust


@router.post("/register", response_model=RegisterOut)
def register_customer(payload: CustomerRegister, db: Session = Depends(get_db)):
    """小程序客户自助注册：创建 User + 关联 Customer（CRM 归集）。

    按手机号去重：已存在客户直接返回（幂等），避免重复建档。
    若传入 openid，则把该微信身份绑定到客户对应的 User 上，
    使静默登录(wx-login)能据此找回客户、退出后自动恢复登录态。
    """
    import re
    if not re.match(r"^1\d{10}$", payload.phone or ""):
        raise HTTPException(400, "手机号格式不正确")

    # 生日格式校验（选填）
    birthday = _validate_md(payload.birthday) if payload.birthday else None
    if payload.birthday and not birthday:
        raise HTTPException(400, "生日格式应为 MM-DD（如 03-15）")

    existing = db.query(Customer).filter(Customer.phone == encrypt_phone(payload.phone)).first()
    if existing:
        # 已注册：补绑定 openid（若缺失），便于后续静默登录找回
        if payload.openid and existing.user_id:
            u = db.query(User).filter(User.id == existing.user_id).first()
            if u and not u.openid:
                u.openid = payload.openid
                db.commit()
        # 首次补全生日（若历史未填）
        if birthday and not existing.birthday:
            existing.birthday = birthday
            db.commit()
        return RegisterOut(
            user_id=existing.user_id or 0,
            customer_id=existing.id,
            nickname=existing.name,
            phone=decrypt_phone(existing.phone),
            birthday=existing.birthday,
            wechat_no=existing.wechat_no,
            already_registered=True,
        )

    user = User(
        nickname=payload.nickname,
        phone=encrypt_phone(payload.phone),
        openid=payload.openid,
        status="active",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    cust = Customer(
        user_id=user.id,
        name=payload.nickname,
        phone=encrypt_phone(payload.phone),
        wechat_no=payload.wechat_no,
        source="miniprogram",
        travel_preference=payload.travel_preference,
        budget_range=payload.budget_range,
        birthday=birthday,
        follow_status="pending_follow",
    )
    db.add(cust)
    db.commit()
    db.refresh(cust)

    return RegisterOut(
        user_id=user.id,
        customer_id=cust.id,
        nickname=user.nickname,
        phone=decrypt_phone(user.phone),
        birthday=cust.birthday,
        wechat_no=cust.wechat_no,
        already_registered=False,
    )


@router.put("/{customer_id}", response_model=CustomerOut)
def update_customer(customer_id: int, payload: CustomerUpdate,
                    _auth=Depends(_auth_customer_writer), db: Session = Depends(get_db)):
    """编辑客户资料（标签 / 备注 / 跟进状态 / 画像等）。"""
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(404, "客户不存在")
    for k, v in payload.model_dump(exclude_unset=True).items():
        if k == "phone" and v is not None:
            v = encrypt_phone(v)
        setattr(cust, k, v)
    db.commit()
    db.refresh(cust)
    return cust


@router.get("/{customer_id}/follow-ups", response_model=list[FollowUpOut])
def list_follow_ups(customer_id: int, _admin=Depends(get_current_admin),
                   db: Session = Depends(get_db)):
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    if not cust:
        raise HTTPException(404, "客户不存在")
    return db.query(FollowUp).filter(FollowUp.customer_id == customer_id).order_by(FollowUp.id.desc()).all()


@router.post("/{customer_id}/follow-ups", response_model=FollowUpOut)
def add_follow_up(customer_id: int, payload: FollowUpCreate,
                 _admin=Depends(get_current_admin), db: Session = Depends(get_db)):
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
