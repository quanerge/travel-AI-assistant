# server/routers/chat.py
# 微信客服消息回传管理后台。
#
# 设计约束：本项目 requirements 不含 cryptography，无法做微信消息安全模式(AES)解密，
# 故微信公众平台须将「消息加解密方式」设为「明文模式」，本文件只解析明文 XML。
#
# 两个入口（统一带 /api 前缀，与项目其它 router 约定一致）：
#   1) /api/wechat/callback  GET  -> 微信服务器验证（回显 echostr）
#                           POST -> 接收客户在客服会话发的消息，存 chat_message(direction=in)
#   2) /api/admin/chat/*      -> 管理后台使用，需管理员 token：
#        GET    sessions       会话列表（按 openid 聚合 + 未读数 + 关联客户昵称/手机）
#        GET    messages       某 openid 的消息记录
#        POST   reply          管理员回复（存 out + 调微信下发客服消息）
#        POST   read           标记某会话已读
import os
import hashlib
import logging
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import ChatMessage, User
from utils.wechat import send_custom_message
from routers.auth import get_current_admin

logger = logging.getLogger("lvguanjia.wechat.chat")

# 微信回调校验 token（公众平台「消息推送」处填写，需与此一致）。可用环境变量覆盖。
_CALLBACK_TOKEN = os.getenv("WECHAT_CALLBACK_TOKEN", "lvguanjia_callback")

# 与项目其它 router 保持一致，统一带 /api 前缀（前端 baseURL=/api；nginx 反代 /api -> 后端）
router = APIRouter(prefix="/api")


# ---------------- 微信回调（无需登录）----------------

@router.get("/wechat/callback")
def wechat_verify(signature: str = "", timestamp: str = "", nonce: str = "", echostr: str = ""):
    """微信服务器接入验证：校验 signature 后回显 echostr。

    明文模式下微信只要求返回 echostr 即通过；此处做宽松校验，
    校验失败时仍回显 echostr，避免配置期被卡死。
    """
    try:
        items = sorted([_CALLBACK_TOKEN, timestamp, nonce])
        sha = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
        if sha == signature:
            return Response(content=echostr, media_type="text/plain")
    except Exception as e:  # noqa: BLE001
        logger.warning("微信回调校验异常: %s", e)
    return Response(content=echostr, media_type="text/plain")


@router.post("/wechat/callback")
async def wechat_receive(request: Request, db: Session = Depends(get_db)):
    """接收客户在客服会话中发送的消息（明文 XML），存入 chat_message。

    无论解析成功与否都返回 "success"，否则微信会按重试策略反复推送。
    """
    body = await request.body()
    try:
        root = ET.fromstring(body)
        msg_type = root.findtext("MsgType")
        openid = root.findtext("FromUserName")
        content = root.findtext("Content")
        if msg_type == "text" and openid and content:
            db.add(ChatMessage(
                openid=openid,
                direction="in",
                msg_type="text",
                content=content,
            ))
            db.commit()
            logger.info("收到客服消息 openid=%s content=%s", openid, content)
    except Exception as e:  # noqa: BLE001
        logger.warning("微信客服消息解析失败: %s", e)
    return Response(content="success", media_type="text/plain")


# ---------------- 管理后台接口（需管理员 token）----------------

class ChatReply(BaseModel):
    openid: str
    content: str


class ChatRead(BaseModel):
    openid: str


@router.get("/admin/chat/sessions")
def chat_sessions(db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """会话列表：按 openid 聚合，返回最近一条消息、未读数、关联客户昵称/手机。"""
    rows = db.query(ChatMessage).all()
    last = {}
    unread = {}
    for m in rows:
        if m.openid not in last or (m.created_at and (last[m.openid].created_at is None or m.created_at > last[m.openid].created_at)):
            last[m.openid] = m
        if m.direction == "in" and not m.is_read:
            unread[m.openid] = unread.get(m.openid, 0) + 1

    openids = list(last.keys())
    users = {}
    if openids:
        for u in db.query(User).filter(User.openid.in_(openids)).all():
            users[u.openid] = u

    result = []
    for openid, m in last.items():
        u = users.get(openid)
        result.append({
            "openid": openid,
            "nickname": u.nickname if u else None,
            "phone": u.phone if u else None,
            "last_content": m.content,
            "last_at": m.created_at.isoformat() if m.created_at else None,
            "unread": unread.get(openid, 0),
        })
    result.sort(key=lambda x: x["last_at"] or "", reverse=True)
    return result


@router.get("/admin/chat/messages")
def chat_messages(openid: str = Query(...), db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """某会话的全部消息，按时间正序。"""
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.openid == openid)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [{
        "id": m.id,
        "direction": m.direction,
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in msgs]


@router.post("/admin/chat/reply")
def chat_reply(payload: ChatReply, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    """管理员回复：先存出站消息，再调微信下发客服消息（48h 互动限制内才可达）。"""
    msg = ChatMessage(
        openid=payload.openid,
        direction="out",
        msg_type="text",
        content=payload.content,
        admin_id=admin.id,
    )
    db.add(msg)
    db.commit()
    delivered = send_custom_message(payload.openid, payload.content)
    if not delivered:
        logger.warning("客服消息下发失败，但已存入后台（openid=%s）", payload.openid)
    return {"status": "ok", "delivered": delivered}


@router.post("/admin/chat/read")
def chat_read(payload: ChatRead, db: Session = Depends(get_db), _admin=Depends(get_current_admin)):
    """标记某会话的入站消息为已读（清除未读红点）。"""
    db.query(ChatMessage).filter(
        ChatMessage.openid == payload.openid,
        ChatMessage.direction == "in",
        ChatMessage.is_read.is_(False),
    ).update({ChatMessage.is_read: True})
    db.commit()
    return {"status": "ok"}
