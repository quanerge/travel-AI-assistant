# server/routers/config.py —— 站点级公开配置（无需登录）
# 顾问联系方式在此集中配置，前端启动时拉取，避免把电话写死在前端/各页面。
# 配置方式：在 .env 设置 ADVISOR_PHONE / ADVISOR_WECHAT / ADVISOR_NAME 等环境变量即可，
# 无需改代码、无需重新发布小程序。
import os
from fastapi import APIRouter

router = APIRouter(prefix="/api/config", tags=["config"])


def _advisor_info():
    return {
        "name": os.getenv("ADVISOR_NAME", "小旅顾问"),
        "phone": os.getenv("ADVISOR_PHONE", ""),       # 纯数字，如 13800000000
        "wechat": os.getenv("ADVISOR_WECHAT", ""),      # 微信号
        "avatar": os.getenv("ADVISOR_AVATAR", ""),
        "intro": os.getenv("ADVISOR_INTRO", "资深旅游顾问，提供一对一行程规划与报名服务"),
        "worktime": os.getenv("ADVISOR_WORKTIME", "9:00 - 21:00"),
    }


@router.get("/advisor")
def get_advisor():
    """公开接口：返回当前对外展示的顾问联系方式（一键拨号 / 复制微信用）。"""
    return _advisor_info()
