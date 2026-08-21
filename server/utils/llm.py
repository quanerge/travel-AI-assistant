# server/utils/llm.py
"""极简 OpenAI 兼容大模型客户端（仅用标准库 urllib，零三方依赖）。

设计要点：
- 兼容所有 /v1/chat/completions 接口的厂商：DeepSeek、通义千问 Qwen、OpenAI、智谱 GLM、Kimi 等。
- API Key 只存在于后端环境变量（LLM_API_KEY），**绝不暴露给小程序**（小程序代码可被反编译）。
- 用 response_format=json_object 强制模型返回 JSON，便于后端结构化解析。
"""
import json
import os
import threading
import urllib.request
from typing import Optional


def _base_url() -> str:
    # 结尾统一补 /v1（DeepSeek: https://api.deepseek.com/v1；Qwen: https://dashscope.aliyuncs.com/compatible-mode/v1）
    return os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")


def _api_key() -> str:
    return os.getenv("LLM_API_KEY", "")


def _model() -> str:
    return os.getenv("LLM_MODEL", "deepseek-chat")


def chat_completion(messages: list, temperature: float = 0.7,
                    max_tokens: int = 1500, timeout: int = 20,
                    json_mode: bool = True) -> str:
    """调用大模型，返回助手文本。失败抛 RuntimeError（由调用方捕获并降级）。

    json_mode: 是否强制 JSON 返回。行程规划用 True（后端结构化解析）；
    自由对话用 False（返回自然语言文本）。
    """
    if not _api_key():
        raise RuntimeError("LLM_API_KEY 未配置，AI 不可用")
    payload = {
        "model": _model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        # 仅结构化规划场景需要 JSON；对话场景传自由文本
        payload["response_format"] = {"type": "json_object"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_base_url()}/chat/completions",
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_api_key()}",
        },
        method="POST",
    )

    # 硬超时保护：把 urlopen 放进守护线程，join 超时即视为失败。
    # 这样即便 DNS/connect 被防火墙静默丢弃导致 urllib 的 timeout 不生效，
    # 也保证本函数最多 (timeout+5)s 内返回，绝不会冻住 uvicorn 工作线程。
    holder: dict = {}

    def _do():
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                holder["body"] = json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            holder["err"] = e

    th = threading.Thread(target=_do, daemon=True)
    th.start()
    th.join(timeout + 5)
    if th.is_alive():
        raise RuntimeError("调用大模型超时（服务不可达或网络被拦截）")
    if "err" in holder:
        raise holder["err"]
    return holder["body"]["choices"][0]["message"]["content"]


def generate_poi_intro(route_name: str, day_title: str, day_content: str) -> list:
    """LLM 把一天的行程文本拆成多个景点解说词，每条 intro ≤50 字（适配微信同声传译插件限制）。

    返回 [{name, intro}, ...]；失败或解析异常时返回空列表（由调用方降级处理）。
    """
    if not _api_key():
        return []
    prompt = (
        f"你是旅游线路语音解说词撰写助手。下面是一条线路某一天的行程信息。\n"
        f"线路名：{route_name}\n"
        f"当天标题：{day_title}\n"
        f"当天行程描述：{day_content}\n\n"
        "请从中提取 2-5 个主要景点/体验点，为每个写一句精炼的中文语音解说词。\n"
        "要求：\n"
        "1. name：简短景点名（不超过12字）；\n"
        "2. intro：一句解说，不超过50个汉字，口语化、适合中老年游客听；\n"
        "3. 只输出 JSON，格式：{\"pois\":[{\"name\":\"...\",\"intro\":\"...\"}]}，不要多余文字。"
    )
    try:
        raw = chat_completion(
            [{"role": "system", "content": "你只输出 JSON，不解释。"},
             {"role": "user", "content": prompt}],
            temperature=0.6, max_tokens=800, timeout=25, json_mode=True,
        )
        data = json.loads(raw)
        out = []
        for p in data.get("pois", []):
            name = (p.get("name") or "").strip()
            intro = (p.get("intro") or "").strip()[:50]
            if name:
                out.append({"name": name, "intro": intro})
        return out
    except Exception:  # noqa: BLE001
        return []


def build_recommend_route(name: str, extract: str) -> Optional[dict]:
    """把 Wikivoyage 抓来的目的地攻略事实，**原创改写**成一篇公众号推文式推荐内容。

    合法性设计：攻略原文为 CC BY-SA 授权（可读事实）；本函数要求模型**基于事实重新创作**，
    禁止复制/引用原文句子与段落（事实本身不受著作权保护，表达才受保护），
    产出为原创中文表达，不侵犯原作者著作权。展示侧仍保留「来源：维基导游」署名与免责。
    返回 dict（字段见下），供后端 upsert 进 WikiGuide.ai_json；失败返回 None（降级：仅保留原文）。
    字段：name, days, destination, summary, daily[{title,content,meals,accommodation,traffic}],
          highlights[list], budget, suitable_crowd, intensity( easy/normal/moderate/challenge )
    """
    if not _api_key():
        return None
    # 攻略文本可能很长，截断避免超 token（保留前 ~4000 字足矣提炼行程）
    excerpt = (extract or "")[:4000]
    prompt = (
        f"你是一位资深旅游公众号主编。下面是一段关于「{name}」的公开旅游资料（维基导游，CC BY-SA）。\n"
        f"请基于其中的**事实信息**（地点、特色、交通、气候等）进行**原创改写**，写成一篇公众号风格的推荐文，并严格输出 JSON。\n\n"
        f"资料原文：\n{excerpt}\n\n"
        "【原创红线——必须遵守】\n"
        "1. 只能用原文中的事实（如“昆明有石林”“大理气候温和”），但表达必须全部重新组织，用自己的话写；\n"
        "2. **严禁**原句照抄、复制或改头换面引用原文的任何句子、短语、列举（“=”开头的目录行更不可出现）；\n"
        "3. 输出的是你的原创中文表达，句句重新写。\n\n"
        "输出 JSON 格式（不要任何多余文字）：\n"
        "{\n"
        '  "name": "公众号式标题（如：云南，一个把心留下的地方｜7日慢游推荐，20字内，钩子开头、口语化、不要出现“经典X日深度游”这种模板）",\n'
        '  "days": 整数参考天数,\n'
        '  "destination": "目的地",\n'
        '  "summary": "推荐语：60-100字，开头有吸引力（如“去对了季节，这里的美会惊艳到你”），讲清“为什么值得去、适合怎么玩”，面向中老年读者",\n'
        '  "daily": [ { "title": "第N天·主题（口语化）", "content": "当天玩法建议（口语化、生动、100字内）", '
        '"meals": "餐饮建议", "accommodation": "住宿建议", "traffic": "交通建议" } ],\n'
        '  "highlights": ["亮点1：必看景点", "亮点2：必吃美食", "亮点3：特色玩法"],\n'
        '  "budget": "人均预算区间描述（如：约3000-5000元/人）",\n'
        '  "suitable_crowd": "适合人群描述",\n'
        '  "intensity": "easy 或 normal 或 moderate 或 challenge"\n'
        "}\n"
        "要求：days 与 daily 数组长度一致（3-8 天）；标题必须是公众号文章风格，禁止“X日深度游/经典X日”模板；"
        "summary 与 daily.content 口语化、有画面感、面向中老年、便于语音播报；所有内容必须原创表达。"
    )
    try:
        raw = chat_completion(
            [{"role": "system", "content": "你只输出 JSON，不解释。"},
             {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=2500, timeout=30, json_mode=True,
        )
        data = json.loads(raw)
        daily = data.get("daily") or []
        if not data.get("name") or not daily:
            return None
        # 规整：days 以 daily 实际条数校正
        data["days"] = len(daily)
        # 默认值兜底
        data.setdefault("destination", name)
        data.setdefault("summary", "")
        data.setdefault("highlights", [])
        data.setdefault("budget", "以实际为准")
        data.setdefault("suitable_crowd", "适合大多数中老年游客")
        data.setdefault("intensity", "normal")
        return data
    except Exception:  # noqa: BLE001
        return None


def ping(timeout: int = 8) -> "tuple[bool, str]":
    """诊断用：用一条极简请求探测大模型是否可达。返回 (ok, error_msg)。"""
    if not _api_key():
        return False, "LLM_API_KEY 未配置（请在 .env 填入真实 key 并重启 uvicorn）"
    try:
        chat_completion(
            [{"role": "user", "content": "ping"}],
            temperature=0, max_tokens=5, timeout=timeout, json_mode=False,
        )
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)
