# server/utils/llm.py
"""极简 OpenAI 兼容大模型客户端（仅用标准库 urllib，零三方依赖）。

设计要点：
- 兼容所有 /v1/chat/completions 接口的厂商：DeepSeek、通义千问 Qwen、OpenAI、智谱 GLM、Kimi 等。
- API Key 只存在于后端环境变量（LLM_API_KEY），**绝不暴露给小程序**（小程序代码可被反编译）。
- 用 response_format=json_object 强制模型返回 JSON，便于后端结构化解析。
"""
import json
import os
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
                    max_tokens: int = 1500, timeout: int = 35) -> str:
    """调用大模型，返回助手文本。失败抛 RuntimeError（由调用方捕获并降级）。"""
    if not _api_key():
        raise RuntimeError("LLM_API_KEY 未配置，AI 规划不可用")
    payload = {
        "model": _model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
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
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]
