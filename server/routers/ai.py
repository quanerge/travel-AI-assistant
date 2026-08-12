# server/routers/ai.py
"""AI 行程自动规划（第二阶段核心能力）。

流程：小程序收集偏好 -> POST /api/ai/plan -> 后端检索线路库作为上下文 ->
调用大模型生成结构化行程 -> 写入 ConsultRecord(channel='ai') ->
小程序在「我的咨询」中查看（复用需求单闭环：顾问可改、可一键转订单）。

绝不从小程序直连大模型：密钥安全 + 微信域名白名单 + CORS。
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database import get_db
from models import ConsultRecord, Route, User, AdminUser, AIConversation, AIMessage
from typing import Optional
from routers.auth import get_current_user, get_current_admin
from utils.llm import chat_completion, ping, _api_key
from schemas import AIChatReq, AIChatResp, AIConversationOut, AIMessageOut

router = APIRouter(prefix="/api/ai", tags=["ai"])

SYSTEM_PROMPT = """你是「旅途管家」的资深旅游规划师，服务于一位个人旅游顾问的私域客户。
请用专业、亲切、可信的口吻，基于客户需求和「现有线路库」给出可落地的多日行程。

必须严格只返回 JSON，结构如下（不要任何额外文字）：
{
  "itinerary": [{"day": 1, "title": "抵达与适应", "desc": "上午抵达X，下午自由活动...", "meals": "午晚餐自理", "accommodation": "当地四星酒店"}],
  "summary": "整体方案概述（2-4 句，突出亮点与适配人群）",
  "cost_estimate": "费用预估拆分，例如：机票约xxx+当地参团xxx+食宿xxx，人均约xxx元（含/不含往返大交通请注明）",
  "route_ids": [与现有线路库匹配的线路 id 列表，若无匹配留空数组],
  "need_human": true
}
注意：
- itinerary 天数必须与客户要求的天数一致；
- 若线路库有匹配产品，优先在 desc 中引用其名称，并放入 route_ids；
- need_human 表示是否建议转人工顾问确认（一般为 true）；
- 费用均为预估，措辞需体现「仅供参考」。
"""


class AIPlanReq(BaseModel):
    destination: str = Field(..., min_length=1, description="目的地")
    days: int = Field(..., ge=1, le=30, description="天数")
    people: int = Field(1, ge=1, description="出行人数")
    budget: str = ""
    departure: str = ""
    preferences: str = ""   # 自由文本：兴趣/亲子/美食/慢游...


class AIPlanResp(BaseModel):
    consult_id: int
    itinerary: list
    summary: str
    cost_estimate: str
    route_ids: list
    need_human: bool
    disclaimer: str = "以上为 AI 预估，仅供参考，最终以顾问确认方案为准。"


def _retrieve_routes(db: Session, destination: str, days: int) -> list:
    """按目的地/天数从线路库检索，作为大模型上下文（RAG-lite）。"""
    q = db.query(Route).filter(Route.status == "active")
    if destination:
        q = q.filter(Route.destination.contains(destination) | Route.name.contains(destination))
    if days:
        q = q.filter(Route.days.between(max(1, days - 1), days + 2))
    return q.limit(8).all()


@router.post("/plan", response_model=AIPlanResp)
def ai_plan(req: AIPlanReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    routes = _retrieve_routes(db, req.destination, req.days)
    route_ctx = "\n".join(
        f"- [{r.id}] {r.name} | 目的地{r.destination} | {r.days}天 | ¥{r.price} | {(r.description or '')[:60]}"
        for r in routes
    ) or "（暂无完全匹配的现成线路，请基于通用旅行知识规划）"

    user_msg = (
        f"请为以下需求规划行程：\n"
        f"目的地：{req.destination}\n天数：{req.days}\n人数：{req.people}\n"
        f"预算：{req.budget or '不限'}\n出发地：{req.departure or '未定'}\n偏好：{req.preferences or '无特殊'}\n\n"
        f"可参考的现有线路库：\n{route_ctx}"
    )

    try:
        raw = chat_completion([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ])
        parsed = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"AI 规划生成失败：{e}")

    itinerary = parsed.get("itinerary", [])
    summary = parsed.get("summary", "")
    cost = parsed.get("cost_estimate", "")
    route_ids = parsed.get("route_ids", []) or []
    need_human = bool(parsed.get("need_human", True))

    # 写入咨询表，复用需求单闭环（我的咨询可见、顾问可改、可一键转订单、未读红点）
    rec = ConsultRecord(
        user_id=user.id,
        channel="ai",
        name=None,
        phone=None,
        content=user_msg,
        itinerary=itinerary,
        reply_content=f"{summary}\n\n【费用预估】{cost}",
        reply_at=datetime.utcnow(),
        reply_by=None,
        status="replied",
    )
    db.add(rec)
    try:
        db.commit()
    except Exception:
        db.rollback()
        db.commit()
    db.refresh(rec)

    return AIPlanResp(
        consult_id=rec.id,
        itinerary=itinerary,
        summary=summary,
        cost_estimate=cost,
        route_ids=route_ids,
        need_human=need_human,
    )


# --------------------------------------------------------------------------- #
# AI 多轮对话（小程序 AI 旅行助手，P0）
# --------------------------------------------------------------------------- #
CHAT_SYSTEM_PROMPT = """你是「旅途管家」的 AI 旅游助手，服务于个人旅游顾问的私域客户。
用专业、亲切、可信的中文口吻回答客户的旅行问题：线路推荐、行程建议、出行注意事项、费用预估等。
可基于客户的提问灵活应答，必要时引导其咨询真人顾问。
费用与时间均为预估，措辞需体现「仅供参考」；不要编造具体航班号、酒店预订或无法核实的报价。
"""


@router.get("/ping")
def ai_ping():
    """诊断端点（无需登录）：检查 LLM key 是否配置、模型是否可达。

    用法：浏览器/手机直接访问 http://<后端IP>:8000/api/ai/ping
    返回示例：{"llm_configured": true, "reachable": true, "error": ""}
    排查：llm_configured=false → .env 没配 key；reachable=false → 后端机器连不上大模型（网络/防火墙/key 无效）。
    """
    ok, err = ping()
    return {"llm_configured": bool(_api_key()), "reachable": ok, "error": err}


@router.post("/chat", response_model=AIChatResp)
def ai_chat(req: AIChatReq, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 1) 定位或新建会话（会话归属当前用户，防越权）
    if req.conversation_id:
        conv = db.query(AIConversation).filter(
            AIConversation.id == req.conversation_id,
            AIConversation.user_id == user.id,
        ).first()
        if not conv:
            raise HTTPException(404, "会话不存在")
    else:
        conv = AIConversation(user_id=user.id, title=req.message[:20])
        db.add(conv)
        db.commit()
        db.refresh(conv)

    # 2) 取最近 20 条历史（按 id 倒序取最新的 20 条，再反转回时间正序）
    history = db.query(AIMessage).filter(
        AIMessage.conversation_id == conv.id
    ).order_by(AIMessage.id.desc()).limit(20).all()[::-1]
    # 防御：若历史末尾是孤立的 user 消息（上次模型调用失败未回、无配对
    # assistant），丢弃它，避免 messages 出现连续两条 user 触发大模型 API
    # 报错，从而陷入"永远失败"的死亡螺旋。
    while history and history[-1].role == "user":
        history.pop()

    # 3) RAG-lite：按用户消息中的目的地检索线路库作为背景知识
    routes = _retrieve_routes(db, req.message, 0)
    route_ctx = "\n".join(
        f"- [{r.id}] {r.name} | 目的地{r.destination} | {r.days}天 | ¥{r.price} | {(r.description or '')[:60]}"
        for r in routes
    ) or "（暂无完全匹配的现成线路）"

    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT + "\n\n可参考的现有线路库：\n" + route_ctx},
    ]
    for m in history:
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": req.message})

    # 4) 调用大模型（自由文本模式，非 JSON）。
    #    注意：先调模型、成功后再一起落库 user+assistant（成对），这样即便
    #    模型调用失败也不会在会话历史留下"孤立的 user 消息"，避免下次续聊时
    #    messages 出现连续两条 user 触发大模型 API 报错、导致会话永远失败。
    try:
        reply = chat_completion(messages, json_mode=False, max_tokens=1200)
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"[AI] 大模型调用失败：{e}")
        db.commit()  # 提交会话归属等已有状态（新建会话已 commit，此处幂等）
        raise HTTPException(502, f"AI 回复生成失败：{e}")

    # 5) 成对落库 用户消息 + 助手消息 + 刷新会话时间
    db.add(AIMessage(conversation_id=conv.id, role="user", content=req.message))
    db.add(AIMessage(conversation_id=conv.id, role="assistant", content=reply))
    conv.updated_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
        db.commit()
    return AIChatResp(conversation_id=conv.id, reply=reply)


@router.get("/conversations", response_model=list[AIConversationOut])
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """当前用户的 AI 会话列表（按最近活跃倒序）。"""
    return db.query(AIConversation).filter(
        AIConversation.user_id == user.id
    ).order_by(AIConversation.updated_at.desc()).all()


@router.get("/chat/history", response_model=list[AIMessageOut])
def chat_history(conversation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """会话历史消息（按时间正序），用于进入旧会话时回放。"""
    conv = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.user_id == user.id,
    ).first()
    if not conv:
        raise HTTPException(404, "会话不存在")
    return db.query(AIMessage).filter(
        AIMessage.conversation_id == conversation_id
    ).order_by(AIMessage.id).all()


# --------------------------------------------------------------------------- #
# AI 智能提取（管理后台「粘贴自动填充」）
# --------------------------------------------------------------------------- #
class AIExtractReq(BaseModel):
    text: str = Field(..., min_length=1, description="待提取的自由文本，如供应商线路资料/行程介绍")


class AIExtractResp(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    departure: Optional[str] = None
    destination: Optional[str] = None
    days: Optional[int] = None
    price: Optional[float] = None
    cost_price: Optional[float] = None
    rating: Optional[float] = None
    group_size: Optional[int] = None
    description: Optional[str] = None
    fee_included: Optional[str] = None
    fee_excluded: Optional[str] = None
    notice: Optional[str] = None
    route_days: Optional[list] = None
    source: Optional[str] = None
    warning: Optional[str] = None


EXTRACT_PROMPT = """你是「旅途管家」的旅游线路信息提取助手。请从用户输入的自由文本中提取旅游线路的结构化字段，只输出一个 JSON，不要任何额外文字。

字段说明（文本中没有则填 null）：
- name: 线路名称（字符串）
- category: 必须从 [国内游,短途游,周边游,出境游,主题游] 中选一个；无法确定则 null
- departure: 出发地（字符串）
- destination: 目的地（字符串）
- days: 行程总天数（整数）
- price: 人均价格（数字，单位元）
- cost_price: 成本价（数字，可选）
- rating: 评分（0-5 的数字，可选）
- group_size: 成团人数（整数，可选）
- description: 行程亮点/描述（字符串）
- fee_included: 费用包含（字符串）
- fee_excluded: 费用不含（字符串）
- notice: 注意事项（字符串）
- route_days: 每日行程数组，每项 {day_no:整数, title:字符串, content:字符串, meals:字符串, accommodation:字符串, traffic:字符串}；无法拆分则 null

要求：字段值必须来自文本，不要编造；价格/天数等数字直接从文本取，不要加工。"""


def _regex_fallback(text: str) -> dict:
    """大模型不可用时的廉价正则兜底，能提多少提多少（规则+LLM 混合的兜底层）。"""
    import re
    out = {}
    m = re.search(r'天数[是为:：]?\s*(\d+)', text)
    if m: out['days'] = int(m.group(1))
    m = re.search(r'(?:价格|单价|人均)[是为:：]?\s*[¥￥]?\s*(\d+)', text)
    if m: out['price'] = float(m.group(1))
    m = re.search(r'目的地[是为:：]?\s*([^\n，。；,]+)', text)
    if m: out['destination'] = m.group(1).strip()
    m = re.search(r'出发地[是为:：]?\s*([^\n，。；,]+)', text)
    if m: out['departure'] = m.group(1).strip()
    m = re.search(r'(?:线路名?称|标题)[是为:：]?\s*([^\n，。；,]+)', text)
    if m: out['name'] = m.group(1).strip()
    return out


@router.post("/extract", response_model=AIExtractResp)
def ai_extract(req: AIExtractReq, admin: AdminUser = Depends(get_current_admin)):
    """管理后台「粘贴自动填充」：从自由文本用大模型抽取线路字段。

    大模型优先；若大模型不可用（超时/错误），自动降级为正则兜底，并在
    warning 中说明，保证后台录入在极端情况下仍能部分自动填充（规则+LLM 混合）。
    """
    try:
        raw = chat_completion([
            {"role": "system", "content": EXTRACT_PROMPT},
            {"role": "user", "content": "待提取文本：\n" + req.text},
        ], json_mode=True, max_tokens=1500)
        # 防御：某些模型会在 JSON 外包 ```json 代码块
        raw = raw.strip()
        if raw.startswith("```"):
            s, e = raw.find("{"), raw.rfind("}")
            raw = raw[s:e + 1] if s != -1 and e != -1 else raw
        data = json.loads(raw)
        data["source"] = "llm"
    except Exception as e:  # noqa: BLE001
        data = _regex_fallback(req.text)
        data["source"] = "regex_fallback"
        data["warning"] = f"大模型提取失败，已用规则兜底：{e}"

    # 类型与范围容错：LLM 可能返回字符串数字或越界值
    for k in ("days", "group_size"):
        if data.get(k) is not None:
            try:
                data[k] = int(float(data[k]))
            except (ValueError, TypeError):
                data[k] = None
    for k in ("price", "cost_price", "rating"):
        if data.get(k) is not None:
            try:
                data[k] = float(data[k])
            except (ValueError, TypeError):
                data[k] = None
    if data.get("rating") is not None:
        data["rating"] = max(0.0, min(5.0, data["rating"]))
    if isinstance(data.get("route_days"), list):
        cleaned = []
        for i, d in enumerate(data["route_days"]):
            if not isinstance(d, dict):
                continue
            cleaned.append({
                "day_no": int(d.get("day_no") or (i + 1)),
                "title": str(d.get("title") or ""),
                "content": str(d.get("content") or ""),
                "meals": str(d.get("meals") or ""),
                "accommodation": str(d.get("accommodation") or ""),
                "traffic": str(d.get("traffic") or ""),
            })
        data["route_days"] = cleaned or None
    return data
