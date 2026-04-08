import hashlib
import json
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path

import pymysql
import redis

MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
MYSQL_USER = os.getenv("MYSQL_USER", "flask_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "flask_pass")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "message_db")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "60"))
MAX_QUERY_LIMIT = int(os.getenv("MAX_QUERY_LIMIT", "100"))

LOG_DIR = Path(os.getenv("LOG_DIR", "/workspace/project-devops/logs"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/workspace/project-devops/backups"))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)


def get_db_connection():
    """获取 MySQL 连接（字典游标）。"""
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        port=MYSQL_PORT,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def init_tables():
    """初始化演示项目所需的业务/运维数据表。"""
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INT PRIMARY KEY AUTO_INCREMENT,
            content TEXT NOT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS monitor_records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            cpu_load DECIMAL(8,2) NOT NULL,
            memory_used_percent DECIMAL(8,2) NOT NULL,
            disk_used_percent DECIMAL(8,2) NOT NULL,
            service_status VARCHAR(50) NOT NULL,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS backup_records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            backup_name VARCHAR(255) NOT NULL,
            backup_path VARCHAR(500) NOT NULL,
            status VARCHAR(50) NOT NULL,
            note VARCHAR(255) DEFAULT '',
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
            restore_time DATETIME NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS alert_records (
            id INT PRIMARY KEY AUTO_INCREMENT,
            level VARCHAR(20) NOT NULL,
            title VARCHAR(120) NOT NULL,
            detail TEXT,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT PRIMARY KEY AUTO_INCREMENT,
            username VARCHAR(64) NOT NULL UNIQUE,
            password_hash VARCHAR(128) NOT NULL,
            role VARCHAR(32) NOT NULL DEFAULT 'viewer',
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            create_time DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]

    conn = get_db_connection()
    with conn.cursor() as cursor:
        for sql in ddl:
            cursor.execute(sql)
    conn.commit()
    conn.close()


def serialize_datetimes(rows):
    """将查询结果中的 datetime 转为字符串，便于 JSON 序列化。"""
    for row in rows:
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
    return rows


def hash_password(raw_password):
    """简单哈希（演示用途）。"""
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


def get_memory_used_percent():
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            lines = f.readlines()
        mem_total = float([x for x in lines if x.startswith("MemTotal")][0].split()[1])
        mem_available = float([x for x in lines if x.startswith("MemAvailable")][0].split()[1])
        return round((1 - mem_available / mem_total) * 100, 2)
    except Exception:
        return 0.0


def get_disk_used_percent():
    usage = shutil.disk_usage("/")
    return round((usage.used / usage.total) * 100, 2)


def collect_metrics_snapshot():
    """采集系统监控快照（负载、内存、磁盘、操作系统信息）。"""
    return {
        "cpu_load": round(os.getloadavg()[0], 2) if hasattr(os, "getloadavg") else 0.0,
        "memory_used_percent": get_memory_used_percent(),
        "disk_used_percent": get_disk_used_percent(),
        "os": platform.platform(),
    }


def build_message_filter_sql(keyword, start_time, end_time):
    """按查询条件动态拼接 where 子句与参数。"""
    where_clauses = []
    params = []
    if keyword:
        where_clauses.append("content LIKE %s")
        params.append(f"%{keyword}%")
    if start_time:
        where_clauses.append("create_time >= %s")
        params.append(start_time)
    if end_time:
        where_clauses.append("create_time <= %s")
        params.append(end_time)

    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    return where_sql, params


def list_messages(keyword="", start_time="", end_time="", limit=20):
    """分页查询消息，带条件过滤与最大条数保护。"""
    safe_limit = min(max(int(limit), 1), MAX_QUERY_LIMIT)
    where_sql, params = build_message_filter_sql(keyword, start_time, end_time)
    sql = f"SELECT id, content, create_time FROM messages{where_sql} ORDER BY id DESC LIMIT %s"

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql, (*params, safe_limit))
        rows = cursor.fetchall()
    conn.close()
    return serialize_datetimes(rows), safe_limit


def message_cache_key(keyword, start_time, end_time, limit):
    return f"query:messages:{keyword}:{start_time}:{end_time}:{limit}"


def read_log_lines(filename, limit=100):
    """读取日志文件最后 N 行。"""
    path = LOG_DIR / filename
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-limit:]]


def set_json_cache(key, value, ttl=CACHE_TTL_SECONDS):
    """将对象序列化后写入 Redis，并设置 TTL。"""
    redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
