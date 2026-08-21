# server/utils/scraper.py
"""网络推荐线路数据源：从 Wikivoyage（维基导游，zh）公开 API 抓取热门目的地攻略。

为什么是 Wikivoyage：
- 公开 MediaWiki API，无反爬、无需鉴权；
- 内容采用 CC BY-SA 授权，允许转载展示，但须署名（展示时保留「来源：维基导游」+ 条目链接）；
- 返回结构化 wiki 文本（含 == 区域 == / == 景点 == 等小节），适合喂给 LLM 加工成「推荐游玩线路」。

零三方依赖：仅用标准库 urllib。所有网络调用带超时与异常兜底，单点失败不影响整体。
"""
import json
import logging
import urllib.parse
import urllib.request
from typing import List, Optional

logger = logging.getLogger("lvguanjia.scraper")

API = "https://zh.wikivoyage.org/w/api.php"
UA = "TravelAIAssistant/1.0 (https://github.com/quanerge/travel-AI-assistant)"

# 与小程序「智能规划」页热门标签保持一致，作为默认抓取池（Wikivoyage 上均为有效条目）
HOT_DESTINATIONS = [
    "云南", "新疆", "西藏", "四川", "海南", "北京", "日本", "东南亚",
]

_TIMEOUT = 20


def _get(url: str) -> Optional[dict]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning("Wikivoyage 请求失败 %s: %s", url, e)
        return None


def search_destinations(keyword: str, limit: int = 5) -> List[dict]:
    """按关键词搜索目的地，返回 [{title, snippet}]。"""
    q = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": keyword,
        "format": "json", "srlimit": limit,
    })
    data = _get(f"{API}?{q}")
    if not data:
        return []
    return [
        {"title": it.get("title", ""), "snippet": _strip_html(it.get("snippet", ""))}
        for it in data.get("query", {}).get("search", [])
    ]


def fetch_destination_extract(title: str) -> Optional[str]:
    """抓取某目的地条目的全文纯文本攻略（Wikitext 已去标记）。失败返回 None。"""
    q = urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": "1",
        "titles": title, "format": "json",
    })
    data = _get(f"{API}?{q}")
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {})
    for pid, page in pages.items():
        if pid == "-1":  # 条目不存在
            continue
        extract = page.get("extract")
        if extract and extract.strip():
            return extract.strip()
    return None


def fetch_hot_extracts() -> List[dict]:
    """抓取默认热门目的地攻略，返回 [{title, extract, url}]。"""
    out = []
    for title in HOT_DESTINATIONS:
        extract = fetch_destination_extract(title)
        if extract:
            out.append({
                "title": title,
                "extract": extract,
                "url": f"https://zh.wikivoyage.org/wiki/{urllib.parse.quote(title)}",
            })
        else:
            logger.warning("热门目的地无攻略：%s", title)
    return out


def _strip_html(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s or "")


def entry_url(title: str) -> str:
    """生成条目的可署名链接（CC BY-SA 要求）。"""
    return f"https://zh.wikivoyage.org/wiki/{urllib.parse.quote(title)}"
