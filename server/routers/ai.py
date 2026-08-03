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
from models import ConsultRecord, Route, User
from routers.auth import get_current_user
from utils.llm import chat_completion

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
