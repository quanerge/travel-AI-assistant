# server/models.py —— 对应需求说明书 V1.1 第 9 章数据库设计
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(64), unique=True, index=True)
    unionid = Column(String(64), nullable=True)
    nickname = Column(String(64), nullable=True)
    avatar = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True)  # 建议加密存储
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(16), default="active")


class Customer(Base):
    __tablename__ = "customer"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    name = Column(String(64))
    wechat_no = Column(String(64), nullable=True)
    phone = Column(String(32), nullable=True)
    source = Column(String(32), nullable=True)
    travel_preference = Column(String(128), nullable=True)
    budget_range = Column(String(32), nullable=True)
    birthday = Column(String(32), nullable=True)             # 生日/纪念日，存 "MM-DD"，用于提醒
    tags = Column(String(255), nullable=True)
    remark = Column(Text, nullable=True)                       # 顾问备注
    follow_status = Column(String(16), default="pending_follow")  # pending_follow/contacting/deal/lost
    last_contact_at = Column(DateTime, nullable=True)         # 最后联系时间
    total_orders = Column(Integer, default=0)
    total_amount = Column(Float, default=0)
    last_trip = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_key = Column(Boolean, default=False, nullable=False)          # 重点客户标注（星标）
    community = Column(String(128), nullable=True)                   # 客户所在小区，用于按小区分组归并
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)


class Route(Base):
    __tablename__ = "route"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128))
    category = Column(String(32))
    cover = Column(String(255), nullable=True)
    gallery = Column(Text, nullable=True)  # JSON 字符串
    days = Column(Integer)
    departure = Column(String(64))
    destination = Column(String(64))
    price = Column(Float)
    cost_price = Column(Float, nullable=True)   # 仅后台
    profit = Column(Float, nullable=True)       # 仅后台，不向前端暴露
    rating = Column(Float, default=5.0)
    signup_count = Column(Integer, default=0)
    group_size = Column(Integer, default=20)
    status = Column(String(16), default="active")
    description = Column(Text, nullable=True)
    fee_included = Column(Text, nullable=True)
    fee_excluded = Column(Text, nullable=True)
    notice = Column(Text, nullable=True)
    created_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    route_days = relationship(
        "RouteDay", back_populates="route",
        cascade="all, delete-orphan", order_by="RouteDay.day_no"
    )


class RouteDay(Base):
    __tablename__ = "route_day"
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("route.id"))
    day_no = Column(Integer)
    title = Column(String(128))
    content = Column(Text, nullable=True)
    meals = Column(String(64), nullable=True)
    accommodation = Column(String(128), nullable=True)
    traffic = Column(String(64), nullable=True)
    route = relationship("Route", back_populates="route_days")


class Order(Base):
    __tablename__ = "order"
    id = Column(Integer, primary_key=True, index=True)
    order_no = Column(String(64), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=True)
    name = Column(String(64))
    phone = Column(String(32))
    person_count = Column(Integer, default=1)
    departure_date = Column(String(32), nullable=True)
    remark = Column(Text, nullable=True)
    status = Column(String(32), default="pending_confirm")
    deposit_amount = Column(Float, default=0)
    deposit_paid = Column(Boolean, default=False)
    total_amount = Column(Float, nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)  # 软删除标记（保留审计与支付记录）
    deleted_at = Column(DateTime, nullable=True)                     # 删除时间
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payment"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("order.id"))
    type = Column(String(16))            # deposit / balance
    amount = Column(Float)
    method = Column(String(16), default="offline")  # wechat / offline
    trade_no = Column(String(64), nullable=True)
    status = Column(String(16), default="pending")
    paid_at = Column(DateTime, nullable=True)
    operator_id = Column(Integer, nullable=True)


class Member(Base):
    __tablename__ = "member"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    level = Column(String(16), default="normal")  # normal / vip / premium
    expire_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)


class Commission(Base):
    __tablename__ = "commission"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("order.id"))
    referrer_user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    type = Column(String(16))            # cash / points / coupon
    amount = Column(Float, default=0)
    status = Column(String(16), default="pending")
    settled_at = Column(DateTime, nullable=True)


class Coupon(Base):
    __tablename__ = "coupon"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(64), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    amount = Column(Float, default=0)
    condition = Column(String(128), nullable=True)
    expire_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="unused")


class ConsultRecord(Base):
    __tablename__ = "consult_record"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    channel = Column(String(32))         # wechat / phone / message / plan
    name = Column(String(64), nullable=True)   # 留言人姓名（用于归集客户）
    phone = Column(String(32), nullable=True)  # 留言人手机（用于归集客户）
    content = Column(Text, nullable=True)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=True, index=True)
    handled_by = Column(Integer, nullable=True)
    status = Column(String(16), default="pending")
    reply_content = Column(Text, nullable=True)        # 顾问方案/回复正文
    reply_at = Column(DateTime, nullable=True)         # 顾问回复时间
    reply_by = Column(Integer, nullable=True)          # 回复顾问 admin id
    customer_read_at = Column(DateTime, nullable=True) # 客户已读时间（用于未读红点）
    attachments = Column(JSON, nullable=True)   # 顾问方案附件（图片 URL 列表）
    itinerary = Column(JSON, nullable=True)     # 行程卡片：[{day, title, desc}]
    is_deleted = Column(Boolean, default=False, nullable=False)  # 软删除标记（保留审计痕迹）
    deleted_at = Column(DateTime, nullable=True)                     # 删除时间
    created_at = Column(DateTime, default=datetime.utcnow)


class AdminUser(Base):
    __tablename__ = "admin_user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True)
    password_hash = Column(String(128))
    role = Column(String(16), default="advisor")  # advisor / super
    phone = Column(String(32), nullable=True)
    status = Column(String(16), default="active")  # active / disabled
    created_at = Column(DateTime, default=datetime.utcnow)


class FollowUp(Base):
    """客户跟进记录：每次顾问联系/沟通留痕。"""
    __tablename__ = "follow_up"
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=False, index=True)
    admin_id = Column(Integer, nullable=True)     # 跟进人（管理员）
    content = Column(Text, nullable=False)        # 跟进内容
    created_at = Column(DateTime, default=datetime.utcnow)


class Banner(Base):
    """首页 Banner 轮播配置（需求 7.1）。"""
    __tablename__ = "banner"
    id = Column(Integer, primary_key=True, index=True)
    image = Column(String(255), nullable=True)          # 轮播图地址
    title = Column(String(128), nullable=True)          # 文案
    route_id = Column(Integer, ForeignKey("route.id"), nullable=True)  # 跳转线路
    sort = Column(Integer, default=0)                   # 展示顺序，越小越靠前
    status = Column(String(16), default="active")       # active / inactive
    created_at = Column(DateTime, default=datetime.utcnow)


class Favorite(Base):
    """用户收藏的线路（需求 7.2 / 我的收藏）。"""
    __tablename__ = "favorite"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    """微信客服消息回传：客户在客服会话发的消息经微信回调存入此处；
    管理员在后台的回复也存入此处（direction=out）。"""
    __tablename__ = "chat_message"
    id = Column(Integer, primary_key=True, index=True)
    openid = Column(String(64), index=True, nullable=False)   # 微信用户 openid（与 user.openid 一致）
    direction = Column(String(8), default="in")               # in=客户→管理员 / out=管理员→客户
    msg_type = Column(String(16), default="text")             # 首版仅 text；后续可扩展 image/voice
    content = Column(Text, nullable=True)                     # 文本消息内容
    admin_id = Column(Integer, nullable=True)                 # 回复的管理员 id（仅 out 消息）
    is_read = Column(Boolean, default=False, nullable=False)  # 客户消息是否已读（in 消息用于未读红点）
    created_at = Column(DateTime, default=datetime.utcnow)
