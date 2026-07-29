# server/routers/consult.py
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from database import get_db
from models import ConsultRecord, User
from schemas import ConsultCreate, ConsultOut
from routers.auth import get_current_admin, get_current_user
from routers.customers import upsert_customer_from_contact
from utils.crypto import encrypt_phone
from utils.pagination import paginate, set_pagination_headers

router = APIRouter(prefix="/api/consult", tags=["consult"])


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
        content=payload.content
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    # 归集客户：留言即潜在客户（按姓名/手机匹配，无订单不累加消费）
    upsert_customer_from_contact(db, name=payload.name, phone=payload.phone, source=payload.channel)
    return rec


@router.get("", response_model=list[ConsultOut])
def list_consult(_admin=Depends(get_current_admin), db: Session = Depends(get_db),
                page: int = None, page_size: int = 50, response: Response = None):
    """咨询列表含客户手机号等 PII，仅管理员可读。"""
    total, items = paginate(
        db.query(ConsultRecord).order_by(ConsultRecord.id.desc()), page, page_size
    )
    set_pagination_headers(response, page, page_size, total)
    return items
