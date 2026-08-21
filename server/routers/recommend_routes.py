# server/routers/recommend_routes.py
"""网络推荐攻略（小程序「发现」tab）：维基导游公开原文 + AI 原创改写（公众号风推荐文）。

合规设计（2026-08-20 用户确认）：
- 数据源：Wikivoyage（维基导游 zh）公开 MediaWiki API，原文 CC BY-SA 授权，展示侧保留署名 source_url。
- 公众号风内容：由 LLM 基于原文**事实**原创改写（prompt 强制不得复制原文句子/段落，见 utils/llm.build_recommend_route），
  产出为原创中文表达，不侵犯原作者著作权；无 key/失败时自动回退展示原文。
- 不做「爬取微信公众号文章」：未经授权转载他人公众号文章即使署名也构成侵犯信息网络传播权（有判例），排除。

- GET  /api/recommend-routes         公开：目的地攻略列表（AI 摘要优先）
- GET  /api/recommend-routes/{id}    公开：攻略详情（AI 原创改写优先 + 原文折叠）
- POST /api/recommend-routes/crawl   管理员：手动触发抓取一批热门目的地（幂等 upsert）

定时：main.py startup 会启动一个标准库 daemon 线程，每天自动 crawl 一次（零新依赖）。
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import WikiGuide, AdminUser
from schemas import WikiGuideOut, WikiGuideDetailOut
from routers.auth import get_current_admin
from utils.scraper import fetch_hot_extracts
from utils.llm import build_recommend_route

logger = logging.getLogger("lvguanjia.recommend_routes")

router = APIRouter(prefix="/api/recommend-routes", tags=["recommend-routes"])

_TEASER_LEN = 80  # 原文摘要长度


def _teaser(content: str) -> str:
    """取原文开头一段作摘要（去首行空白/空行/目录行）。"""
    text = (content or "").strip()
    if not text:
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    if lines[0].startswith("="):
        lines = lines[1:]
    return (lines[0] if lines else "")[:_TEASER_LEN]


def _parse_blocks(content: str) -> list:
    """把 wiki 纯文本解析成 [{type: heading|text|list, text}]，供阅读页逐项渲染。"""
    blocks = []
    buf = []
    for raw in (content or "").splitlines():
        ln = raw.rstrip()
        stripped = ln.strip()
        if not stripped:
            continue
        if stripped.startswith("==") and stripped.endswith("=="):
            if buf:
                blocks.append({"type": "text", "text": " ".join(buf)})
                buf = []
            title = stripped.strip("=").strip()
            if title:
                blocks.append({"type": "heading", "text": title})
        elif stripped.startswith(("*", "#")):
            if buf:
                blocks.append({"type": "text", "text": " ".join(buf)})
                buf = []
            item = stripped.lstrip("*#").strip()
            if item:
                blocks.append({"type": "list", "text": item})
        else:
            buf.append(stripped)
    if buf:
        blocks.append({"type": "text", "text": " ".join(buf)})
    return blocks


def _load_ai(g: WikiGuide) -> dict:
    """读取 ai_json 缓存（容错：损坏视为无）。"""
    if not g.ai_json:
        return {}
    try:
        data = json.loads(g.ai_json)
        return data if isinstance(data, dict) else {}
    except (ValueError, TypeError):
        return {}


@router.get("", response_model=list[WikiGuideOut])
def list_recommend_routes(db: Session = Depends(get_db)):
    """发现页公开列表：AI 原创改写优先，无则回退原文（新到旧）。"""
    rows = db.query(WikiGuide).order_by(WikiGuide.id.desc()).all()
    out = []
    for r in rows:
        ai = _load_ai(r)
        out.append(WikiGuideOut(
            id=r.id,
            title=r.title,
            display_name=(ai.get("name") or "").strip() or r.title,
            teaser=(ai.get("summary") or "").strip() or _teaser(r.content),
            has_ai=bool(ai),
            source_url=r.source_url,
            updated_at=r.updated_at,
        ))
    return out


@router.get("/{guide_id}", response_model=WikiGuideDetailOut)
def get_recommend_guide(guide_id: int, db: Session = Depends(get_db)):
    """攻略详情：AI 原创改写优先展示；raw_blocks 供「查看原文」折叠。"""
    g = db.query(WikiGuide).filter(WikiGuide.id == guide_id).first()
    if not g:
        raise HTTPException(404, "攻略不存在")
    ai = _load_ai(g)
    plan = []
    for i, d in enumerate(ai.get("daily") or [], start=1):
        plan.append({
            "day_no": i,
            "title": (d.get("title") or f"第{i}天").strip(),
            "content": (d.get("content") or "").strip(),
            "meals": (d.get("meals") or "").strip(),
            "accommodation": (d.get("accommodation") or "").strip(),
            "traffic": (d.get("traffic") or "").strip(),
        })
    return WikiGuideDetailOut(
        id=g.id,
        title=g.title,
        mode="ai" if ai else "raw",
        ai_name=(ai.get("name") or "").strip() or g.title,
        ai_summary=(ai.get("summary") or "").strip(),
        ai_highlights=[str(h) for h in (ai.get("highlights") or [])],
        ai_plan=plan,
        ai_budget=(ai.get("budget") or "").strip(),
        ai_crowd=(ai.get("suitable_crowd") or "").strip(),
        raw_blocks=_parse_blocks(g.content),
        source_url=g.source_url,
        updated_at=g.updated_at,
    )


def crawl_recommend_routes(db: Session, sources: list = None) -> dict:
    """抓取热门目的地攻略原文 + AI 原创改写，幂等 upsert 入库。

    sources: 缺省用 scraper.HOT_DESTINATIONS；每项 {title, extract, url}。
    返回统计 {crawled, created, updated, ai_ok, ai_fail, skipped}。
    AI 改写失败/无 key 不致命：原文照常入库，前端回退原文。
    """
    srcs = sources if sources is not None else fetch_hot_extracts()
    stats = {"crawled": 0, "created": 0, "updated": 0, "ai_ok": 0, "ai_fail": 0, "skipped": 0}
    for item in srcs:
        title = (item.get("title") or "").strip()
        extract = (item.get("extract") or "").strip()
        url = item.get("url") or ""
        if not title or not extract:
            stats["skipped"] += 1
            continue
        stats["crawled"] += 1
        existing = db.query(WikiGuide).filter(WikiGuide.title == title).first()
        if existing:
            existing.content = extract
            existing.source_url = url
            stats["updated"] += 1
        else:
            existing = WikiGuide(title=title, content=extract, source_url=url)
            db.add(existing)
            db.flush()
            stats["created"] += 1
        # AI 原创改写（失败不影响原文；仅在有原文时尝试）
        plan = build_recommend_route(title, extract)
        if plan:
            existing.ai_json = json.dumps(plan, ensure_ascii=False)
            stats["ai_ok"] += 1
        else:
            existing.ai_json = None
            stats["ai_fail"] += 1
    try:
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        logger.error("攻略入库失败：%s", e)
        stats["skipped"] = stats.get("skipped", 0) + 1
    return stats


@router.post("/crawl")
def manual_crawl(user: AdminUser = Depends(get_current_admin), db: Session = Depends(get_db)):
    """管理员手动触发一次热门目的地抓取（幂等，可重复点）。"""
    stats = crawl_recommend_routes(db)
    return {"ok": True, **stats}
