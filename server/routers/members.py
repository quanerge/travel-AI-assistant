# server/routers/members.py —— 会员体系（激活 member 表，功能4）
# 当前提供「我的会员」只读接口；付费开通/积分变动由后台顾问操作，后续可扩展。
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Member, User
from schemas import MemberOut
from routers.auth import get_current_user

logger = logging.getLogger("lvguanjia.members")

router = APIRouter(prefix="/api/members", tags=["members"])

# 等级展示名映射（member.level_name 为空时回退）
_LEVEL_NAMES = {"normal": "普通会员", "vip": "VIP会员", "premium": "高级会员"}
# 未开通会员时的默认权益说明（引导升级）
_DEFAULT_RIGHTS = "AI 行程规划 / 专属顾问咨询"


@router.get("/me", response_model=MemberOut)
def get_my_member(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """返回当前登录用户的会员信息；无记录时返回普通会员默认值（is_member=false）。"""
    m = db.query(Member).filter(Member.user_id == current_user.id).first()
    if not m:
        return MemberOut(
            level="normal", level_name=_LEVEL_NAMES["normal"],
            points=0, total_points=0, rights=_DEFAULT_RIGHTS, is_member=False
        )
    level_name = m.level_name or _LEVEL_NAMES.get(m.level, "普通会员")
    return MemberOut(
        id=m.id,
        level=m.level,
        level_name=level_name,
        points=m.points or 0,
        total_points=m.total_points or 0,
        rights=m.rights or _DEFAULT_RIGHTS,
        expire_at=m.expire_at,
        status=m.status or "active",
        is_member=True,
    )
