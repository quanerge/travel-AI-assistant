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
