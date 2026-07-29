# server/database.py
# 默认使用 SQLite 便于零依赖启动；生产可设置环境变量 DATABASE_URL 切换到 MySQL。
# 例如：DATABASE_URL="mysql+pymysql://user:pwd@host:3306/lvguanjia?charset=utf8mb4"
import os
import sqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lvguanjia.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate():
    """为已存在的表补齐新列（SQLite 不支持 ALTER COLUMN IF NOT EXISTS）。

    全新库由 create_all 直接建好带新列的表；历史库则靠这里 ADD COLUMN。
    列已存在时 SQLite 会报 duplicate column，捕获后忽略即可。
    """
    alters = [
        ("customer", "remark", "TEXT"),
        ("customer", "follow_status", "VARCHAR(16)"),
        ("customer", "last_contact_at", "DATETIME"),
        ("customer", "birthday", "VARCHAR(32)"),
        ("consult_record", "name", "VARCHAR(64)"),
        ("consult_record", "phone", "VARCHAR(32)"),
        ("consult_record", "route_id", "INTEGER"),
        ("consult_record", "reply_content", "TEXT"),
        ("consult_record", "reply_at", "DATETIME"),
        ("consult_record", "reply_by", "INTEGER"),
        ("consult_record", "customer_read_at", "DATETIME"),
        ("consult_record", "attachments", "TEXT"),
        ("consult_record", "itinerary", "TEXT"),
        ("consult_record", "is_deleted", "INTEGER"),
        ("consult_record", "deleted_at", "DATETIME"),
        ("admin_user", "status", "VARCHAR(16)"),
        ("admin_user", "phone", "VARCHAR(32)"),
    ]
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        for table, col, ctype in alters:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}")
            except (OperationalError, sqlite3.OperationalError):
                # 列已存在（或表结构已是最新），忽略。
                # raw_connection 抛的是底层 sqlite3.OperationalError，必须一并捕获。
                pass
        conn.commit()
    finally:
        conn.close()
