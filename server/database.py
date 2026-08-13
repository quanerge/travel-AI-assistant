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
        ("order", "is_deleted", "INTEGER"),
        ("order", "deleted_at", "DATETIME"),
        ("coupon", "title", "VARCHAR(128)"),
        ("coupon", "applicable", "VARCHAR(64)"),
        ("order", "coupon_id", "INTEGER"),
        ("order", "discount_amount", "FLOAT"),
        ("order", "deposit_amount", "FLOAT"),
        ("order", "cost_snapshot", "FLOAT"),
        ("customer", "is_key", "INTEGER"),
        ("customer", "community", "VARCHAR(128)"),
        ("customer", "is_deleted", "INTEGER"),
        ("customer", "deleted_at", "DATETIME"),
        # 功能1：线路强度维度
        ("route", "intensity_level", "VARCHAR(16)"),
        ("route", "max_altitude", "INTEGER"),
        ("route", "suitable_crowd", "VARCHAR(128)"),
        ("route", "daily_walk", "INTEGER"),
        ("route", "suitable_age_min", "INTEGER"),
        ("route", "suitable_age_max", "INTEGER"),
    ]
    conn = engine.raw_connection()
    try:
        cur = conn.cursor()
        for table, col, ctype in alters:
            try:
                # 表名加双引号转义（order 是 SQLite 保留字，必须引号；其余表加引号也安全）
                cur.execute(f'ALTER TABLE "{table}" ADD COLUMN {col} {ctype}')
            except (OperationalError, sqlite3.OperationalError):
                # 列已存在（或表结构已是最新），忽略。
                # raw_connection 抛的是底层 sqlite3.OperationalError，必须一并捕获。
                pass
        conn.commit()
        # 修复：coupon.code 曾被误设为 UNIQUE（见 models.py），导致用户领取时复制模板 code
        # 触发唯一约束冲突、领券必失败。仅当 ix_coupon_code 仍为 UNIQUE 时删除该索引，
        # 避免误删修复后（普通索引）的同名索引。
        try:
            row = cur.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name='ix_coupon_code'"
            ).fetchone()
            if row and row[0] and "UNIQUE" in row[0].upper():
                cur.execute("DROP INDEX ix_coupon_code")
        except (OperationalError, sqlite3.OperationalError):
            pass
        conn.commit()
        # 历史行经 ALTER COLUMN 新增布尔列后值为 NULL，统一回填为 0（False），
        # 否则下游 Pydantic 序列化（bool 字段收到 None）会抛 500，导致客户列表整体不可用。
        for col in ("is_deleted", "is_key"):
            try:
                cur.execute(f'UPDATE "customer" SET {col} = 0 WHERE {col} IS NULL')
            except (OperationalError, sqlite3.OperationalError):
                pass
        conn.commit()
    finally:
        conn.close()
