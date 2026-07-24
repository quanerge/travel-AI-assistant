# server/routers/consult.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import ConsultRecord
from schemas import ConsultCreate, ConsultOut
from routers.customers import upsert_customer_from_contact

router = APIRouter(prefix="/api/consult", tags=["consult"])


@router.post("", response_model=ConsultOut)
def create_consult(payload: ConsultCreate, db: Session = Depends(get_db)):
    """咨询/智能需求单提交（MVP：plan 通道由顾问人工回执）。"""
    rec = ConsultRecord(
        user_id=payload.user_id,
        channel=payload.channel,
        name=payload.name,
        phone=payload.phone,
        content=payload.content
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    # 归集客户：留言即潜在客户（按姓名/手机匹配，无订单不累加消费）
    upsert_customer_from_contact(db, name=payload.name, phone=payload.phone, source=payload.channel)
    return rec


@router.get("", response_model=list[ConsultOut])
def list_consult(db: Session = Depends(get_db)):
    return db.query(ConsultRecord).order_by(ConsultRecord.id.desc()).all()
