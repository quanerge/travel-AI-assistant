# server/models.py —— 对应需求说明书 V1.1 第 9 章数据库设计
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey, JSON, UniqueConstraint
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
    # —— 适老化强度维度（功能1：线路强度标签）——
    intensity_level = Column(String(16), default="normal")   # easy / normal / moderate / challenge
    max_altitude = Column(Integer, nullable=True)            # 最高海拔（米）
    suitable_crowd = Column(String(128), nullable=True)      # 适合人群/年龄描述
    daily_walk = Column(Integer, nullable=True)              # 每日步行量（公里）
    suitable_age_min = Column(Integer, nullable=True)        # 适合年龄下限
    suitable_age_max = Column(Integer, nullable=True)        # 适合年龄上限
    ai_highlight = Column(Text, nullable=True)                # AI 亮点解读缓存（JSON 字符串：顾问/小程序读取，避免每次调 LLM）
    # —— 线路来源（网络推荐功能）：official=本社自营，recommend=从 Wikivoyage 等公开源抓取并经 LLM 加工 ——
    source = Column(String(16), default="official")
    source_url = Column(String(255), nullable=True)           # 来源条目链接（CC BY-SA 署名用）
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
    pois = relationship(
        "RoutePoi", back_populates="day",
        cascade="all, delete-orphan", order_by="RoutePoi.seq"
    )


class RoutePoi(Base):
    """逐景点语音解说词：由 LLM 从 route_day.content 自动拆出并缓存，供小程序逐景点语音播报。
    intro 控制 ≤50 字以适配微信同声传译插件 textToSpeech 的长度限制。"""
    __tablename__ = "route_poi"
    id = Column(Integer, primary_key=True, index=True)
    route_day_id = Column(Integer, ForeignKey("route_day.id"), nullable=False, index=True)
    seq = Column(Integer, default=0)
    name = Column(String(128))
    intro = Column(Text, nullable=True)
    day = relationship("RouteDay", back_populates="pois")


class WikiGuide(Base):
    """目的地攻略原文（发现页）：直接照搬 Wikivoyage 公开条目纯文本 + AI 原创改写版推荐。

    内容为 CC BY-SA 授权，展示侧须保留「来源：维基导游」+ 条目链接（source_url）。
    ai_json 为 LLM 基于原文事实**原创改写**的公众号风推荐文（不复制原文表达），
    无 key/失败时为 NULL，前端自动回退展示原文。
    """
    __tablename__ = "wiki_guide"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(128), unique=True, index=True)   # 目的地名（条目名）
    content = Column(Text, nullable=True)                   # 攻略原文纯文本（explaintext）
    source_url = Column(String(255), nullable=True)         # 维基导游条目链接（署名用）
    ai_json = Column(Text, nullable=True)                   # AI 原创改写 JSON（name/summary/highlights/daily...）
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    deposit_paid = Column(Boolean, default=False)
    total_amount = Column(Float, nullable=True)
    coupon_id = Column(Integer, nullable=True)            # 使用的优惠券 id（下单抵扣）
    discount_amount = Column(Float, default=0)            # 优惠抵扣金额
    deposit_amount = Column(Float, default=0)             # 预估定金（下单时按线路价比例固化）
    cost_snapshot = Column(Float, nullable=True)          # 下单时固化的线路成本快照（人×单价），保证利润可回溯
    balance_amount = Column(Float, default=0)             # 应收尾款 = 总额 - 优惠抵扣 - 定金（下单时固化）
    balance_paid = Column(Boolean, default=False)         # 尾款是否已收（顾问后台线下确认收款）
    settled_at = Column(DateTime, nullable=True)          # 结算时间（尾款收齐，需求 §470 settled_at）
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
    level_name = Column(String(32), nullable=True)  # 等级展示名（如 VIP会员/高级会员）
    points = Column(Integer, default=0)            # 积分余额
    total_points = Column(Integer, default=0)      # 累计积分
    rights = Column(Text, nullable=True)           # 权益说明（逗号分隔文本）
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
    code = Column(String(64), index=True)  # 批次标识：模板与用户券实例共享；绝不能 unique，否则领券复刻 code 必冲突
    title = Column(String(128), nullable=True)   # 优惠券名称（领取页/后台展示）
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    amount = Column(Float, default=0)
    condition = Column(String(128), nullable=True)  # 使用门槛，如"满3000可用"
    applicable = Column(String(64), default="all", nullable=True)  # all=全场 / route:<id> / category:<cat>
    expire_at = Column(DateTime, nullable=True)
    status = Column(String(16), default="unused")  # 模板: active/inactive；用户券: unused/used/expired


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


class AIConversation(Base):
    """AI 多轮对话会话（小程序 AI 旅行助手）。

    user_id 关联私域客户；admin_id 预留给后台「AI 辅助回复」场景（P1）。
    """
    __tablename__ = "ai_conversation"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    admin_id = Column(Integer, nullable=True)                 # 预留：后台顾问代聊场景
    title = Column(String(128), nullable=True)                # 首条消息截断作为标题
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AIMessage(Base):
    """AI 会话的单条消息（user / assistant）。"""
    __tablename__ = "ai_message"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversation.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)                # user / assistant
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    """用户对线路的公开评价（评分 + 文字 + 晒图）。功能①评价晒图。

    不强制绑定订单，先放开 UGC 积累口碑；status 默认 approved 直接展示，
    pending/rejected 预留后台审核流（第二阶段）。
    """
    __tablename__ = "review"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=False, index=True)
    rating = Column(Integer, default=5)                     # 1-5 星
    content = Column(Text, nullable=True)                   # 评价文字
    images = Column(Text, nullable=True)                    # 晒图 URL 列表，JSON 字符串存储
    status = Column(String(16), default="approved")         # approved / pending / rejected
    created_at = Column(DateTime, default=datetime.utcnow)


class RouteRecommend(Base):
    """线路亮点自动分发：客户在小程序产生意向（收藏/咨询/下单）即由系统自动推送该线路
    的 AI 亮点给该客户；客户在「我的推荐」中确认接受后状态回写，顾问零操作即可在后台
    看到谁接受了推荐。

    一个用户对同一条线路仅保留一条推荐记录（user_id + route_id 唯一约束），幂等 upsert。
    highlight_json 预生成并缓存，客户端直接读取，避免每次打开都调大模型。
    """
    __tablename__ = "route_recommend"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("customer.id"), nullable=True, index=True)
    route_id = Column(Integer, ForeignKey("route.id"), nullable=False, index=True)
    status = Column(String(16), default="pending")      # pending / accepted / declined
    highlight_json = Column(Text, nullable=True)        # 预生成的 AI 亮点（JSON 字符串）
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    declined_at = Column(DateTime, nullable=True)
    __table_args__ = (
        UniqueConstraint("user_id", "route_id", name="uq_user_route_recommend"),
    )
