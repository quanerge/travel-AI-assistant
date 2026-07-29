# server/utils/wechat.py
# 微信订阅消息推送（P2）：顾问回复方案后通知客户。
# 纯标准库实现，不引入第三方依赖；配置不全或推送失败时静默降级，不阻断主流程。
import os
import json
import time
import logging
import urllib.request

logger = logging.getLogger("lvguanjia.wechat")

_APPID = os.getenv("WECHAT_APPID")
_APPSECRET = os.getenv("WECHAT_SECRET")
_TMPL = os.getenv("WX_SUBSCRIBE_TMPL_ID")

# access_token 缓存（微信默认 7200s 有效，提前 60s 刷新）
_token = {"value": None, "exp": 0}


def _get_access_token():
    """获取并缓存 access_token（client_credential 方式）。配置缺失返回 None。"""
    global _token
    if _token["value"] and _token["exp"] > time.time() + 60:
        return _token["value"]
    if not (_APPID and _APPSECRET):
        return None
    url = ("https://api.weixin.qq.com/cgi-bin/token"
           f"?grant_type=client_credential&appid={_APPID}&secret={_APPSECRET}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "travel-ai/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("access_token"):
            _token = {"value": data["access_token"],
                      "exp": time.time() + int(data.get("expires_in", 7200))}
            return _token["value"]
        logger.warning("微信获取 access_token 失败: %s", data)
    except Exception as e:  # noqa: BLE001
        logger.warning("微信 access_token 请求异常: %s", e)
    return None


def send_subscribe_message(openid, data, page="pages/myConsult/myConsult"):
    """发送一次性订阅消息。失败返回 False（调用方不应依赖它成功）。

    data 形如 {"thing1": {"value": "..."}, "name2": {...}, "time3": {...}}，
    字段名需与微信公众平台「订阅消息」模板的关键词一致（默认用：
    事项 thing1 / 处理人 name2 / 时间 time3）。模板 id 取自 WX_SUBSCRIBE_TMPL_ID。
    """
    token = _get_access_token()
    if not token or not _TMPL:
        logger.info("微信订阅消息未配置(appid/secret/template)，跳过推送")
        return False
    payload = {
        "touser": openid,
        "template_id": _TMPL,
        "page": page,
        "data": data,
    }
    url = f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={token}"
    try:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("errcode") == 0:
            return True
        # 用户未授权(errcode 43101)等：仅记录，不影响回复已保存
        logger.warning("微信订阅消息发送失败: %s", result)
    except Exception as e:  # noqa: BLE001
        logger.warning("微信订阅消息请求异常: %s", e)
    return False


def send_custom_message(openid, content):
    """向用户下发客服消息（文本）。用于管理员在后台回复客户。

    前置：用户需在 48 小时内与小程序客服有过交互（微信限制）。
    失败返回 False，调用方不应依赖其成功（如超时被微信拒收）。
    """
    token = _get_access_token()
    if not token:
        logger.info("微信客服消息未配置(appid/secret)，跳过下发")
        return False
    if not openid or not content:
        return False
    payload = {
        "touser": openid,
        "msgtype": "text",
        "text": {"content": content},
    }
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        if result.get("errcode") == 0:
            return True
        logger.warning("微信客服消息下发失败: %s", result)
    except Exception as e:  # noqa: BLE001
        logger.warning("微信客服消息请求异常: %s", e)
    return False
