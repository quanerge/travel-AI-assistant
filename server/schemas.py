# server/schemas.py
import json
from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, List
from datetime import datetime
from utils.crypto import decrypt_phone


class RoutePoiOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    route_day_id: int
    seq: int = 0
    name: str
    intro: Optional[str] = None


class WikiGuideOut(BaseModel):
    """发现页目的地攻略（列表卡）。display_name/teaser 优先取 AI 原创改写，无则回退原文。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    display_name: str = ""      # 卡片标题：AI 标题优先，回退目的地名
    teaser: str = ""            # 卡片摘要：AI 推荐语优先，回退原文首段
    has_ai: bool = False        # 是否已生成 AI 原创改写
    source_url: Optional[str] = None
    updated_at: Optional[datetime] = None


class WikiGuideDetailOut(BaseModel):
    """攻略详情：AI 原创改写优先展示；raw_blocks 为原文（供「查看原文」折叠）。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    mode: str = "raw"                     # ai=有原创改写 / raw=仅原文
    ai_name: str = ""
    ai_summary: str = ""
    ai_highlights: List[str] = []
    ai_plan: List[dict] = []              # [{day_no,title,content,meals,accommodation,traffic}]
    ai_budget: str = ""
    ai_crowd: str = ""
    raw_blocks: List[dict] = []           # 原文 [{type: heading|text|list, text}]
    source_url: Optional[str] = None
    updated_at: Optional[datetime] = None


class RouteDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    day_no: int
    title: str
    content: Optional[str] = None
    meals: Optional[str] = None
    accommodation: Optional[str] = None
    traffic: Optional[str] = None
    pois: List[RoutePoiOut] = []   # 逐景点语音解说词（LLM 生成并缓存）


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
    intensity_level: Optional[str] = "normal"
    max_altitude: Optional[int] = None
    suitable_crowd: Optional[str] = None
    daily_walk: Optional[int] = None
    suitable_age_min: Optional[int] = None
    suitable_age_max: Optional[int] = None
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
    intensity_level: Optional[str] = None
    max_altitude: Optional[int] = None
    suitable_crowd: Optional[str] = None
    daily_walk: Optional[int] = None
    suitable_age_min: Optional[int] = None
    suitable_age_max: Optional[int] = None
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
    intensity_level: Optional[str] = None
    max_altitude: Optional[int] = None
    suitable_crowd: Optional[str] = None
    daily_walk: Optional[int] = None
    suitable_age_min: Optional[int] = None
    suitable_age_max: Optional[int] = None
    source: str = "official"                 # official=本社自营 / recommend=网络推荐
    source_url: Optional[str] = None         # 来源条目链接（CC BY-SA 署名）
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

    @field_validator("source", mode="before")
    @classmethod
    def _default_source(cls, v):
        """存量数据 source 列为 NULL（migrate ADD COLUMN 无默认值），统一归一为 official，避免序列化 500。"""
        return v or "official"


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    level: str = "normal"
    level_name: Optional[str] = None
    points: int = 0
    total_points: int = 0
    rights: Optional[str] = None
    expire_at: Optional[datetime] = None
    status: str = "active"
    is_member: bool = False


class OrderCreate(BaseModel):
    route_id: Optional[int] = None
    name: str
    phone: str
    person_count: int = 1
    departure_date: Optional[str] = None
    remark: Optional[str] = None
    user_id: Optional[int] = None
    coupon_id: Optional[int] = None  # 下单抵扣使用的优惠券 id（服务端校验后计算优惠）


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_no: str
    route_id: Optional[int] = None
    route_name: Optional[str] = None
    name: str
    phone: str
    person_count: int
    departure_date: Optional[str] = None
    remark: Optional[str] = None
    status: str
    deposit_paid: bool
    total_amount: Optional[float] = None
    coupon_id: Optional[int] = None
    discount_amount: Optional[float] = 0
    deposit_amount: Optional[float] = 0
    cost_snapshot: Optional[float] = None
    balance_amount: Optional[float] = 0
    balance_paid: Optional[bool] = False
    settled_at: Optional[datetime] = None
    is_deleted: Optional[bool] = None
    deleted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @field_validator("phone", mode="before")
    @classmethod
    def _dec_order_phone(cls, v):
        """DB 中手机号按 enc: 前缀加密存储，读取时解密还原。"""
        return decrypt_phone(v)

    @field_validator("balance_amount", "discount_amount", "deposit_amount", mode="before")
    @classmethod
    def _coerce_order_num(cls, v):
        """历史行经 ALTER COLUMN 加浮点列后可能为 NULL，统一归约为 0，避免前端显示 null。"""
        return v if v is not None else 0

    @field_validator("balance_paid", mode="before")
    @classmethod
    def _coerce_balance_paid(cls, v):
        """历史行 balance_paid 可能为 NULL，归约为 False，避免 Pydantic 序列化 500。"""
        return bool(v) if v is not None else False


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
    name: Optional[str] = None
    phone: Optional[str] = None
    route_id: Optional[int] = None
    route_name: Optional[str] = None
    content: Optional[str] = None
    status: str
    handled_by: Optional[int] = None
    reply_content: Optional[str] = None
    reply_at: Optional[datetime] = None
    customer_read_at: Optional[datetime] = None
    attachments: Optional[list] = None        # 方案附件图片 URL 列表
    itinerary: Optional[list] = None          # 行程卡片：[{day, title, desc}]
    is_deleted: Optional[bool] = None         # 软删除标记
    deleted_at: Optional[datetime] = None     # 删除时间
    created_at: Optional[datetime] = None

    @field_validator("phone", mode="before")
    @classmethod
    def _dec_consult_phone(cls, v):
        """DB 中手机号按 enc: 前缀加密存储，读取时解密还原。"""
        return decrypt_phone(v)


class ConsultUpdate(BaseModel):
    status: Optional[str] = None
    handled_by: Optional[int] = None
    reply_content: Optional[str] = None
    attachments: Optional[list] = None        # 方案附件图片 URL 列表
    itinerary: Optional[list] = None          # 行程卡片：[{day, title, desc}]


class ConsultToOrder(BaseModel):
    """小程序「对此方案下单」：从需求单一键转为订单。

    姓名/手机/线路取自该需求单（缺省时回退到关联客户），此处仅补充
    出行人数、出发日期、备注等下单必要项。
    """
    person_count: Optional[int] = 1
    departure_date: Optional[str] = None
    remark: Optional[str] = None


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
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    is_key: bool = False
    community: Optional[str] = None

    @field_validator("phone", mode="before")
    @classmethod
    def _dec_customer_phone(cls, v):
        """DB 中手机号按 enc: 前缀加密存储，读取时解密还原。"""
        return decrypt_phone(v)

    @field_validator("is_deleted", "is_key", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        """容错：历史行经 ALTER COLUMN 加布尔列后可能为 NULL，
        Pydantic v2 拒绝 None→bool 会导致列表接口 500。统一将 None/0/1 归约为 bool。"""
        return bool(v) if v is not None else False


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
    is_key: Optional[bool] = False
    community: Optional[str] = None


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
    is_key: Optional[bool] = None
    community: Optional[str] = None


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


class CouponOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: Optional[str] = None
    title: Optional[str] = None
    user_id: Optional[int] = None
    amount: float = 0
    condition: Optional[str] = None
    applicable: Optional[str] = "all"  # all=全场 / route:<id> / category:<cat>
    expire_at: Optional[datetime] = None
    status: str = "unused"
    created_at: Optional[datetime] = None
    claimed: bool = False  # 领券中心用：当前登录用户是否已领取该批次模板（非落库字段）


class CouponCreate(BaseModel):
    title: str
    amount: float
    condition: Optional[str] = None
    applicable: str = "all"
    expire_at: Optional[datetime] = None
    status: str = "active"  # 模板默认启用可领


class CouponUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = None
    condition: Optional[str] = None
    applicable: Optional[str] = None
    expire_at: Optional[datetime] = None
    status: Optional[str] = None


# ---- AI 多轮对话（小程序 AI 旅行助手，P0）----
class AIChatReq(BaseModel):
    message: str = Field(..., min_length=1, description="用户本轮消息")
    conversation_id: Optional[int] = None   # 不传则新建会话


class AIChatResp(BaseModel):
    conversation_id: int
    reply: str
    disclaimer: str = "以上为 AI 建议，仅供参考，不构成承诺价格或服务承诺。"


class AIConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AIMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: Optional[datetime] = None


class ReviewIn(BaseModel):
    route_id: int
    rating: int = 5
    content: Optional[str] = None
    images: Optional[List[str]] = None


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    route_id: int
    rating: int
    content: Optional[str] = None
    images: Optional[List[str]] = None
    status: str = "approved"
    nickname: Optional[str] = None   # 评价人昵称（脱敏，不含手机）
    avatar: Optional[str] = None
    created_at: Optional[datetime] = None

    @field_validator("images", mode="before")
    @classmethod
    def _parse_images(cls, v):
        """DB 中以 JSON 字符串存储，读取时解析为列表。"""
        if isinstance(v, str):
            if not v.strip():
                return []
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return [s.strip() for s in v.split(",") if s.strip()]
        return v or []
