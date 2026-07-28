# server/schemas.py
import json
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from utils.crypto import decrypt_phone


class RouteDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_no: int
    title: str
    content: Optional[str] = None
    meals: Optional[str] = None
    accommodation: Optional[str] = None
    traffic: Optional[str] = None


class RouteDayCreate(BaseModel):
    day_no: int
    title: str
    content: Optional[str] = None
    meals: Optional[str] = None
    accommodation: Optional[str] = None
    traffic: Optional[str] = None


class RouteCreate(BaseModel):
    name: str
    category: str
    days: int
    departure: str
    destination: str
    price: float
    cover: Optional[str] = None
    rating: float = 5.0
    group_size: int = 20
    status: str = "active"
    description: Optional[str] = None
    fee_included: Optional[str] = None
    fee_excluded: Optional[str] = None
    notice: Optional[str] = None
    cost_price: Optional[float] = None
    profit: Optional[float] = None
    gallery: Optional[List[str]] = None
    route_days: List[RouteDayCreate] = []


class RouteUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    days: Optional[int] = None
    departure: Optional[str] = None
    destination: Optional[str] = None
    price: Optional[float] = None
    cover: Optional[str] = None
    rating: Optional[float] = None
    group_size: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None
    fee_included: Optional[str] = None
    fee_excluded: Optional[str] = None
    notice: Optional[str] = None
    cost_price: Optional[float] = None
    profit: Optional[float] = None
    gallery: Optional[List[str]] = None
    # 传了则整体替换每日行程；不传则保持不变
    route_days: Optional[List[RouteDayCreate]] = None


class RouteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    category: str
    cover: Optional[str] = None
    gallery: Optional[List[str]] = None
    days: int
    departure: str
    destination: str
    price: float
    cost_price: Optional[float] = None
    profit: Optional[float] = None
    rating: float
    signup_count: int
    group_size: int
    status: str
    description: Optional[str] = None
    fee_included: Optional[str] = None
    fee_excluded: Optional[str] = None
    notice: Optional[str] = None
    route_days: List[RouteDayOut] = []

    @field_validator("gallery", mode="before")
    @classmethod
    def _parse_gallery(cls, v):
        """DB 中以 JSON 字符串存储，读取时解析为列表。"""
        if isinstance(v, str):
            if not v.strip():
                return []
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return [s.strip() for s in v.split(",") if s.strip()]
        return v


class OrderCreate(BaseModel):
    route_id: Optional[int] = None
    name: str
    phone: str
    person_count: int = 1
    departure_date: Optional[str] = None
    remark: Optional[str] = None
    user_id: Optional[int] = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    route_id: Optional[int] = None
    name: str
    phone: str
    person_count: int
    departure_date: Optional[str] = None
    remark: Optional[str] = None
    status: str
    deposit_paid: bool
    total_amount: Optional[float] = None
    created_at: Optional[datetime] = None

    @field_validator("phone", mode="before")
    @classmethod
    def _dec_order_phone(cls, v):
        """DB 中手机号按 enc: 前缀加密存储，读取时解密还原。"""
        return decrypt_phone(v)


class ConsultCreate(BaseModel):
    channel: str = "message"
    content: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    route_id: Optional[int] = None
    user_id: Optional[int] = None


class ConsultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    channel: str
    content: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    wechat_no: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    travel_preference: Optional[str] = None
    budget_range: Optional[str] = None
    birthday: Optional[str] = None
    tags: Optional[str] = None
    last_trip: Optional[str] = None
    remark: Optional[str] = None
    follow_status: Optional[str] = None
    total_orders: int
    total_amount: float
    last_contact_at: Optional[datetime] = None

    @field_validator("phone", mode="before")
    @classmethod
    def _dec_customer_phone(cls, v):
        """DB 中手机号按 enc: 前缀加密存储，读取时解密还原。"""
        return decrypt_phone(v)


class CustomerCreate(BaseModel):
    name: str
    wechat_no: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    travel_preference: Optional[str] = None
    budget_range: Optional[str] = None
    birthday: Optional[str] = None
    tags: Optional[str] = None
    remark: Optional[str] = None
    follow_status: Optional[str] = "pending_follow"


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    wechat_no: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[str] = None
    travel_preference: Optional[str] = None
    budget_range: Optional[str] = None
    birthday: Optional[str] = None
    tags: Optional[str] = None
    remark: Optional[str] = None
    follow_status: Optional[str] = None


class CustomerRegister(BaseModel):
    """小程序客户自助注册入参。"""
    nickname: str
    phone: str
    wechat_no: Optional[str] = None
    travel_preference: Optional[str] = None
    budget_range: Optional[str] = None
    birthday: Optional[str] = None  # 生日，存 "MM-DD"，用于生日关怀提醒
    openid: Optional[str] = None  # 微信身份，用于关联客户与静默登录，实现退出后自动恢复


class RegisterOut(BaseModel):
    """注册/登录返回：供小程序写入登录态。"""
    user_id: int
    customer_id: int
    nickname: str
    phone: str
    birthday: Optional[str] = None
    wechat_no: Optional[str] = None
    already_registered: bool = False


class FollowUpCreate(BaseModel):
    content: str


class FollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    admin_id: Optional[int] = None
    content: str
    created_at: Optional[datetime] = None


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str


class AdminLoginOut(BaseModel):
    """登录成功返回：token + 管理员基本信息（前端存储用于鉴权）。"""
    token: str
    id: int
    username: str
    role: str


class BannerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image: Optional[str] = None
    title: Optional[str] = None
    route_id: Optional[int] = None
    sort: int = 0
    status: str = "active"


class BannerCreate(BaseModel):
    image: Optional[str] = None
    title: Optional[str] = None
    route_id: Optional[int] = None
    sort: int = 0
    status: str = "active"


class BannerUpdate(BaseModel):
    image: Optional[str] = None
    title: Optional[str] = None
    route_id: Optional[int] = None
    sort: Optional[int] = None
    status: Optional[str] = None


class FavoriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int] = None
    route_id: Optional[int] = None
    created_at: Optional[datetime] = None
