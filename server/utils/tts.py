# server/utils/tts.py
"""语音合成 TTS：把景点解说词文本合成为 mp3，供小程序 InnerAudioContext 播放。

采用百度语音合成 REST（纯标准库 urllib，零三方依赖）：
- 用 API Key + Secret Key 换取 access_token（token 缓存到模块级，过期前复用）
- POST text2audio 返回 mp3 字节

零配置降级：未设置 BAIDU_TTS_API_KEY / BAIDU_TTS_SECRET_KEY 时 synthesize() 返回 None，
调用方据此告知小程序「语音暂不可用」（不阻断页面）。

替代路线 B 说明：原方案用微信同声传译插件（端上实时合成），但小程序后台未备案时
插件市场搜索不到、无法添加。改用后端预生成 mp3 完全不依赖微信插件，未备案也能开发/真机调试。
"""
import json
import os
import threading
import time
import urllib.parse
import urllib.request
from typing import Optional

# 百度 access_token 模块级缓存（有效期约 30 天，按 25 天提前刷新）
_TOKEN = {"value": "", "expire": 0.0}
_TOKEN_LOCK = threading.Lock()


def _api_key() -> str:
    return os.getenv("BAIDU_TTS_API_KEY", "")


def _secret_key() -> str:
    return os.getenv("BAIDU_TTS_SECRET_KEY", "")


def _get_token() -> str:
    """换取百度 access_token；模块级缓存避免每次合成重复请求。"""
    if not _api_key() or not _secret_key():
        raise RuntimeError("BAIDU_TTS 密钥未配置")
    now = time.time()
    with _TOKEN_LOCK:
        if _TOKEN["value"] and now < _TOKEN["expire"]:
            return _TOKEN["value"]
    url = (
        "https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials"
        f"&client_id={urllib.parse.quote(_api_key())}"
        f"&client_secret={urllib.parse.quote(_secret_key())}"
    )
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="POST")
    holder: dict = {}

    def _do():
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                holder["body"] = json.loads(resp.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            holder["err"] = e

    th = threading.Thread(target=_do, daemon=True)
    th.start()
    th.join(15)
    if th.is_alive():
        raise RuntimeError("获取百度 token 超时")
    if "err" in holder:
        raise holder["err"]
    body = holder["body"]
    if not isinstance(body, dict) or "access_token" not in body:
        raise RuntimeError("获取百度 token 失败: " + str(body))
    tok = body["access_token"]
    with _TOKEN_LOCK:
        _TOKEN["value"] = tok
        _TOKEN["expire"] = time.time() + 25 * 86400
    return tok


def synthesize(text: str) -> Optional[bytes]:
    """把文本合成为 mp3 字节；无 key / 文本为空 / 合成失败均返回 None。"""
    if not text or not text.strip():
        return None
    if not _api_key() or not _secret_key():
        return None
    try:
        tok = _get_token()
    except Exception:  # noqa: BLE001
        return None
    params = {
        "tex": text,
        "tok": tok,
        "cuid": "lvguanjia",
        "ctp": "1",
        "lan": "zh",
        "spd": "5",   # 语速 0-15，默认 5
        "pit": "5",   # 音调 0-15
        "vol": "5",   # 音量 0-15
        "per": "4",   # 度丫丫（标准女声，适合景点解说）
        "aue": "3",   # 3=mp3
    }
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(
        "https://tsn.baidu.com/text2audio",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    holder: dict = {}

    def _do():
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                holder["ct"] = resp.headers.get("Content-Type", "")
                holder["body"] = resp.read()
        except Exception as e:  # noqa: BLE001
            holder["err"] = e

    th = threading.Thread(target=_do, daemon=True)
    th.start()
    th.join(20)
    if th.is_alive() or "err" in holder:
        return None
    # 百度出错时 Content-Type 为 application/json；正常为 audio/mp3
    if "json" in (holder.get("ct") or ""):
        return None
    return holder.get("body") or None
