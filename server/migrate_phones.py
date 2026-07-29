# server/migrate_phones.py
# 一次性迁移：将历史明文手机号加密为 enc: 前缀密文。
# - 可重复执行（已加密的会跳过，不会产生重复密文）。
# - 依赖 server 同目录的 database 与 utils.crypto，需在 server 目录下运行：
#       cd server && python migrate_phones.py
# - 加密为确定性（同明文→同密文），故不影响按手机号去重/归集逻辑。
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.exc import OperationalError
from database import engine
from utils.crypto import encrypt_phone

# 表名 -> 待加密的手机号列（仅枚举实际存储手机号的表）
TARGETS = {
    "customer": ["phone"],
    "user": ["phone"],
    "order": ["phone"],
    "consult_record": ["phone"],
    "admin_user": ["phone"],
}


def main():
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        total = 0
        for table, cols in TARGETS.items():
            for col in cols:
                # 表/列可能不存在（如全新库尚未建表），跳过即可
                try:
                    cur.execute(f"SELECT id, {col} FROM {table}")
                except (OperationalError, Exception):
                    continue
                rows = cur.fetchall()
                for r in rows:
                    rid, val = r[0], r[1]
                    if val and not str(val).startswith("enc:"):
                        enc = encrypt_phone(str(val))
                        cur.execute(
                            f"UPDATE {table} SET {col}=? WHERE id=?", (enc, rid)
                        )
                        total += 1
                conn.commit()
        print(f"迁移完成：共加密 {total} 条历史明文手机号（已加密的自动跳过）。")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
