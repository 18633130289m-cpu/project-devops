import json
from datetime import datetime

import pymysql
from flask import Blueprint, jsonify, request

from extensions import (
    BACKUP_DIR,
    CACHE_TTL_SECONDS,
    collect_metrics_snapshot,
    get_db_connection,
    hash_password,
    init_tables,
    list_messages,
    message_cache_key,
    read_log_lines,
    redis_client,
    serialize_datetimes,
    set_json_cache,
)

api_bp = Blueprint("api", __name__)


@api_bp.route("/api/messages", methods=["GET", "POST"])
def messages_api():
    if request.method == "POST":
        content = request.form.get("content", "").strip()
        if not content:
            return jsonify({"code": 400, "msg": "Empty"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO messages (content) VALUES (%s)", (content,))
        conn.commit()
        conn.close()

        for key in redis_client.scan_iter("query:messages:*"):
            redis_client.delete(key)
        redis_client.delete("hot:messages")
        return jsonify({"code": 200, "msg": "Successful"})

    keyword = request.args.get("keyword", "").strip()
    start_time = request.args.get("start_time", "").strip()
    end_time = request.args.get("end_time", "").strip()
    limit = request.args.get("limit", "20").strip() or "20"

    cache_key = message_cache_key(keyword, start_time, end_time, limit)
    cache_data = redis_client.get(cache_key)
    if cache_data:
        return jsonify({"code": 200, "source": "redis", "cache_ttl": redis_client.ttl(cache_key), "data": json.loads(cache_data)})

    rows, safe_limit = list_messages(keyword, start_time, end_time, limit)
    set_json_cache(cache_key, rows)
    if not keyword and not start_time and not end_time:
        set_json_cache("hot:messages", rows[:5])

    return jsonify({"code": 200, "source": "mysql", "cache_ttl": CACHE_TTL_SECONDS, "limit": safe_limit, "data": rows})


@api_bp.route("/add", methods=["POST"])
def add_compat_api():
    return messages_api()


@api_bp.route("/list", methods=["GET"])
def list_compat_api():
    return messages_api()


@api_bp.route("/api/health")
@api_bp.route("/health")
def health_api():
    try:
        conn = get_db_connection()
        conn.close()
        mysql_status = "connected"
    except Exception as exc:
        mysql_status = f"failed: {exc}"

    try:
        redis_client.ping()
        redis_status = "connected"
    except Exception as exc:
        redis_status = f"failed: {exc}"

    return jsonify({"mysql": mysql_status, "redis": redis_status, "time": datetime.utcnow().isoformat()})


@api_bp.route("/api/metrics")
def metrics_api():
    current = collect_metrics_snapshot()
    health = health_api().json
    service_status = "ok" if health["mysql"] == "connected" and health["redis"] == "connected" else "degraded"

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("INSERT INTO monitor_records (cpu_load, memory_used_percent, disk_used_percent, service_status) VALUES (%s, %s, %s, %s)", (current["cpu_load"], current["memory_used_percent"], current["disk_used_percent"], service_status))
        cursor.execute("SELECT cpu_load, memory_used_percent, disk_used_percent, service_status, create_time FROM monitor_records ORDER BY id DESC LIMIT 20")
        history = cursor.fetchall()
    conn.commit()
    conn.close()

    current["service_status"] = service_status
    set_json_cache("dashboard:state", current)
    return jsonify({"code": 200, "current": current, "history": serialize_datetimes(history)})


@api_bp.route("/api/backups", methods=["GET", "POST"])
def backups_api():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if request.method == "POST":
        note = request.form.get("note", "").strip()
        now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{now}.tar.gz"
        backup_path = str(BACKUP_DIR / backup_name)

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO backup_records (backup_name, backup_path, status, note) VALUES (%s, %s, %s, %s)", (backup_name, backup_path, "created", note))
        conn.commit()
        conn.close()

        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(f"demo backup file created at {datetime.utcnow().isoformat()}\n")

        return jsonify({"code": 200, "msg": "backup created", "backup_name": backup_name})

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, backup_name, backup_path, status, note, create_time, restore_time FROM backup_records ORDER BY id DESC")
        rows = cursor.fetchall()
    conn.close()
    return jsonify({"code": 200, "data": serialize_datetimes(rows)})


@api_bp.route("/api/backups/<int:backup_id>/restore", methods=["POST"])
def restore_backup_api(backup_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM backup_records WHERE id=%s", (backup_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"code": 404, "msg": "backup not found"}), 404
        cursor.execute("UPDATE backup_records SET status=%s, restore_time=NOW() WHERE id=%s", ("restored", backup_id))
    conn.commit()
    conn.close()
    return jsonify({"code": 200, "msg": "restore done", "backup_id": backup_id})


@api_bp.route("/api/users", methods=["GET", "POST"])
def users_api():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "viewer").strip() or "viewer"

        if not username or not password:
            return jsonify({"code": 400, "msg": "username/password required"}), 400

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)", (username, hash_password(password), role))
            conn.commit()
        except pymysql.err.IntegrityError:
            conn.close()
            return jsonify({"code": 409, "msg": "username exists"}), 409
        conn.close()
        redis_client.delete("cache:users")
        return jsonify({"code": 200, "msg": "user created"})

    cached = redis_client.get("cache:users")
    if cached:
        return jsonify({"code": 200, "source": "redis", "data": json.loads(cached)})

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, username, role, is_active, create_time FROM users ORDER BY id DESC")
        rows = cursor.fetchall()
    conn.close()
    rows = serialize_datetimes(rows)
    set_json_cache("cache:users", rows)
    return jsonify({"code": 200, "source": "mysql", "data": rows})


@api_bp.route("/api/alerts", methods=["GET", "POST"])
def alerts_api():
    if request.method == "POST":
        level = request.form.get("level", "info").strip()
        title = request.form.get("title", "").strip()
        detail = request.form.get("detail", "").strip()
        if not title:
            return jsonify({"code": 400, "msg": "title required"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO alert_records (level, title, detail) VALUES (%s, %s, %s)", (level, title, detail))
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "alert recorded"})

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, level, title, detail, create_time FROM alert_records ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
    conn.close()
    return jsonify({"code": 200, "data": serialize_datetimes(rows)})


@api_bp.route("/api/logs")
def logs_api():
    filename = request.args.get("filename", "access.log")
    limit = min(max(int(request.args.get("limit", "200")), 1), 500)
    if filename not in {"access.log", "error.log"}:
        return jsonify({"code": 400, "msg": "filename must be access.log or error.log"}), 400

    lines = read_log_lines(filename, limit)
    return jsonify({"code": 200, "filename": filename, "limit": limit, "lines": lines})


@api_bp.route("/api/stats")
def stats_api():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS c FROM messages")
        message_count = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM monitor_records")
        monitor_count = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM backup_records")
        backup_count = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM alert_records")
        alert_count = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(*) AS c FROM users")
        user_count = cursor.fetchone()["c"]
    conn.close()

    cache_keys = len(list(redis_client.scan_iter("*")))
    return jsonify({"code": 200, "db_counts": {"messages": message_count, "monitor_records": monitor_count, "backup_records": backup_count, "alert_records": alert_count, "users": user_count}, "redis_keys": cache_keys})


def setup_app_data():
    init_tables()
