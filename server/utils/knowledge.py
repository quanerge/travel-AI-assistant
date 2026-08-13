# server/utils/knowledge.py
"""文件型旅游知识库（零三方依赖，纯标准库）。

设计要点：
- 知识以 Markdown 文件存放在 ``server/knowledge/`` 目录，每个文件一条知识。
- 文件头部用 HTML 注释写 metadata：``<!-- category: 目的地 | tags: 云南,大理 -->``，
  正文从第一个 ``# 标题`` 起。无需 YAML 解析器，正则即可。
- 检索：关键词/子串命中打分（标题 > 标签 > 分类 > 正文），取 top-K。
  语义较弱但零依赖、可控、贴合现有"极简"风格；后续要更强语义可升级向量方案。
- 缓存：按目录文件最新 mtime 缓存，启动时加载一次，文件变更才重读，避免每次请求读盘。

可用环境变量覆盖：
- KNOWLEDGE_DIR：知识目录（默认 server/knowledge）
- KNOWLEDGE_TOP_K：每次返回条数（默认 3）
"""
import glob
import os
import re
from typing import Optional

_DEFAULT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge")
_KB_DIR = os.getenv("KNOWLEDGE_DIR") or _DEFAULT_DIR
try:
    _TOP_K = int(os.getenv("KNOWLEDGE_TOP_K", "3"))
except ValueError:
    _TOP_K = 3

_CACHE: dict = {"items": None, "mtime": 0.0}

_META_RE = re.compile(
    r"<!--\s*category:\s*(?P<cat>[^|]*?)\s*\|\s*tags:\s*(?P<tags>[^>]*?)\s*-->",
    re.IGNORECASE,
)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)
_TERM_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[a-zA-Z]{2,}", re.UNICODE)


def _parse_file(path: str) -> dict:
    """解析单个 Markdown 知识文件为 dict。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = _META_RE.search(text)
    category = m.group("cat").strip() if m else ""
    tags = [t.strip() for t in m.group("tags").split(",") if t.strip()] if m else []
    tm = _TITLE_RE.search(text)
    title = tm.group(1).strip() if tm else os.path.splitext(os.path.basename(path))[0]
    body = _META_RE.sub("", text).strip()
    return {
        "title": title,
        "category": category,
        "tags": tags,
        "body": body,
        "file": os.path.basename(path),
    }


def _load(force: bool = False) -> list:
    """加载全部知识（带 mtime 缓存）。失败返回空列表，不抛异常。"""
    global _CACHE
    try:
        paths = glob.glob(os.path.join(_KB_DIR, "*.md"))
        if not paths:
            return []
        newest = max(os.path.getmtime(p) for p in paths)
        if not force and _CACHE["items"] is not None and newest <= _CACHE["mtime"]:
            return _CACHE["items"]
        items = [_parse_file(p) for p in paths]
        _CACHE = {"items": items, "mtime": newest}
        return items
    except Exception:  # noqa: BLE001
        # 任何异常（目录不存在/读取失败）都降级为空，不影响主流程
        return _CACHE.get("items") or []


def _score(item: dict, query: str) -> int:
    """相关性打分：标题/标签/分类命中权重高于正文。"""
    q = (query or "").lower()
    if not q:
        return 0
    score = 0
    title = item["title"].lower()
    if title and (title in q or q in title):
        score += 5
    for t in item.get("tags", []):
        if t.lower() and t.lower() in q:
            score += 3
    if item.get("category") and item["category"].lower() in q:
        score += 2
    body = item["body"].lower()
    for term in _TERM_RE.findall(q):
        if term in body:
            score += 1
    return score


def retrieve(query: str, top_k: Optional[int] = None) -> list:
    """按查询返回最相关的 top-K 条知识（含 title/category/tags/body/file）。"""
    top_k = top_k or _TOP_K
    items = _load()
    if not query or not items:
        return []
    scored = [(s, it) for it in items if (s := _score(it, query)) > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:top_k]]


def list_knowledge() -> list:
    """返回知识库条目清单（不含正文），供后台/调试查看。"""
    return [
        {
            "title": i["title"],
            "category": i["category"],
            "tags": i["tags"],
            "file": i["file"],
            "chars": len(i["body"]),
        }
        for i in _load()
    ]
