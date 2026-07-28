# server/utils/crypto.py —— 手机号可逆加密（满足个保法"存储加密"要求）
#
# 设计取舍：
# - 仅用标准库（hashlib / base64 / os），不引入 cryptography 等新依赖，避免破坏服务启动。
# - 采用「PBKDF2 派生密钥 + 流密码 XOR」：确定性加密（相同明文 → 相同密文），
#   因此数据库里仍可用 `phone == encrypt(明文)` 做等值查询（客户去重/归集）。
# - 密文带 `enc:` 前缀；decrypt 遇非前缀值原样返回，兼容历史明文数据，可平滑升级。
# - ⚠️ MVP 级强度（非 AES/GCM），生产建议替换为 Fernet(KMS) 并定期轮换密钥。
#    密钥来自环境变量 PHONE_ENCRYPT_KEY，务必在生产环境设置强随机值。

import os
import base64
import hashlib

_SECRET = os.getenv("PHONE_ENCRYPT_KEY", "lvguanjia-dev-phone-secret-change-me")
_KEY = hashlib.pbkdf2_hmac("sha256", _SECRET.encode("utf-8"), b"lvguanjia-phone-salt", 100_000)
_PREFIX = "enc:"


def _xor(data: bytes) -> bytes:
    return bytes(b ^ _KEY[i % len(_KEY)] for i, b in enumerate(data))


def encrypt_phone(plain: str | None) -> str | None:
    """加密手机号；空值原样返回。"""
    if not plain:
        return plain
    return _PREFIX + base64.urlsafe_b64encode(_xor(plain.encode("utf-8"))).decode("ascii")


def decrypt_phone(cipher: str | None) -> str | None:
    """解密手机号；非本工具密文（历史明文/None）原样返回，保证向后兼容。"""
    if not cipher or not cipher.startswith(_PREFIX):
        return cipher
    try:
        return _xor(base64.urlsafe_b64decode(cipher[len(_PREFIX):])).decode("utf-8")
    except Exception:
        return cipher
