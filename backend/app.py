import hashlib
import json
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path

import pymysql
import redis
from flask import Flask, jsonify, request

app = Flask(__name__)

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
    for row in rows:
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.strftime("%Y-%m-%d %H:%M:%S")
    return rows


def hash_password(raw_password):
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


def build_message_filter_sql(keyword, start_time, end_time):
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

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def list_messages(keyword="", start_time="", end_time="", limit=20):
    safe_limit = min(max(int(limit), 1), MAX_QUERY_LIMIT)
    where_sql, params = build_message_filter_sql(keyword, start_time, end_time)
    sql = (
        "SELECT id, content, create_time FROM messages"
        f"{where_sql}"
        " ORDER BY id DESC LIMIT %s"
    )

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql, (*params, safe_limit))
        rows = cursor.fetchall()
    conn.close()

    return serialize_datetimes(rows), safe_limit


def message_cache_key(keyword, start_time, end_time, limit):
    return f"query:messages:{keyword}:{start_time}:{end_time}:{limit}"


def read_log_lines(filename, limit=100):
    path = LOG_DIR / filename
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-limit:]]


init_tables()


# ---------------------- frontend pages ----------------------
@app.route("/")
def dashboard_page():
    return """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>DevOps 管理控制台</title>
  <style>
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, Arial, sans-serif; background: #f4f6fb; }
    header { background: #111827; color: #fff; padding: 16px 20px; }
    .layout { display: grid; grid-template-columns: 230px 1fr; min-height: calc(100vh - 64px); }
    nav { background: #1f2937; color: #cbd5e1; padding: 16px; }
    nav button { width: 100%; margin-bottom: 8px; text-align: left; border: 0; padding: 10px 12px; border-radius: 8px; background: #374151; color: #f9fafb; cursor: pointer; }
    nav button.active { background: #2563eb; }
    main { padding: 20px; }
    .card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 10px rgba(0,0,0,.08); margin-bottom: 16px; }
    .row { display: grid; grid-template-columns: repeat(4, minmax(120px, 1fr)); gap: 10px; }
    input, select, textarea { width: 100%; box-sizing: border-box; padding: 9px; border: 1px solid #d1d5db; border-radius: 8px; }
    button.primary { background: #2563eb; color: #fff; border: 0; padding: 10px 14px; border-radius: 8px; cursor: pointer; }
    table { width: 100%; border-collapse: collapse; }
    th, td { padding: 8px; border-bottom: 1px solid #e5e7eb; text-align: left; font-size: 14px; }
    .hidden { display: none; }
    .badge { padding: 2px 8px; border-radius: 999px; color: #fff; font-size: 12px; }
    .ok { background: #10b981; }
    .cache { background: #ef4444; }
  </style>
</head>
<body>
  <header><h2 style="margin:0;">DevOps 项目控制台</h2></header>
  <div class="layout">
    <nav>
      <button class="active" onclick="switchTab('management', this)">管理页面</button>
      <button onclick="switchTab('monitor', this)">监控面板</button>
      <button onclick="switchTab('backup', this)">备份记录页面</button>
      <button onclick="switchTab('logs', this)">日志查看页面</button>
    </nav>
    <main>
      <section id="management" class="tab">
        <div class="card">
          <h3>留言管理</h3>
          <div class="row">
            <input id="msgContent" placeholder="输入留言" />
            <input id="keyword" placeholder="关键词" />
            <input id="startTime" placeholder="开始时间 2026-04-01 00:00:00" />
            <input id="endTime" placeholder="结束时间 2026-04-30 23:59:59" />
          </div>
          <div style="margin-top:10px;display:flex;gap:8px;">
            <button class="primary" onclick="addMessage()">新增留言</button>
            <button class="primary" onclick="loadMessages()">查询留言</button>
          </div>
          <p id="msgHint"></p>
          <table><thead><tr><th>ID</th><th>内容</th><th>时间</th></tr></thead><tbody id="msgTable"></tbody></table>
        </div>

        <div class="card">
          <h3>用户管理</h3>
          <div class="row">
            <input id="username" placeholder="用户名" />
            <input id="password" type="password" placeholder="密码" />
            <select id="role"><option value="admin">admin</option><option value="operator">operator</option><option value="viewer">viewer</option></select>
            <button class="primary" onclick="createUser()">创建用户</button>
          </div>
          <table style="margin-top:10px;"><thead><tr><th>ID</th><th>用户名</th><th>角色</th><th>状态</th><th>创建时间</th></tr></thead><tbody id="userTable"></tbody></table>
        </div>
      </section>

      <section id="monitor" class="tab hidden">
        <div class="card">
          <h3>监控面板</h3>
          <p id="metricsLine">加载中...</p>
          <table><thead><tr><th>时间</th><th>CPU</th><th>内存</th><th>磁盘</th><th>状态</th></tr></thead><tbody id="monitorTable"></tbody></table>
        </div>
      </section>

      <section id="backup" class="tab hidden">
        <div class="card">
          <h3>备份/恢复</h3>
          <div style="display:flex;gap:8px;align-items:center;">
            <input id="backupNote" placeholder="备份备注" />
            <button class="primary" onclick="createBackup()">创建备份</button>
          </div>
          <table style="margin-top:10px;"><thead><tr><th>ID</th><th>备份名</th><th>状态</th><th>创建时间</th><th>操作</th></tr></thead><tbody id="backupTable"></tbody></table>
        </div>
      </section>

      <section id="logs" class="tab hidden">
        <div class="card">
          <h3>日志查看</h3>
          <div style="display:flex;gap:8px;align-items:center;">
            <select id="logType"><option value="access.log">access.log</option><option value="error.log">error.log</option></select>
            <button class="primary" onclick="loadLogs()">加载日志</button>
          </div>
          <textarea id="logArea" rows="16" style="margin-top:10px;font-family:monospace;"></textarea>
        </div>
      </section>
    </main>
  </div>

<script>
function switchTab(id, el) {
  document.querySelectorAll('.tab').forEach(x => x.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
  document.querySelectorAll('nav button').forEach(x => x.classList.remove('active'));
  el.classList.add('active');
}

async function addMessage() {
  const content = document.getElementById('msgContent').value.trim();
  if (!content) return;
  const res = await fetch('/api/messages', { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:new URLSearchParams({content}) });
  const data = await res.json();
  document.getElementById('msgHint').innerText = data.msg || '';
  document.getElementById('msgContent').value = '';
  await loadMessages();
}

async function loadMessages() {
  const q = new URLSearchParams({
    keyword: document.getElementById('keyword').value.trim(),
    start_time: document.getElementById('startTime').value.trim(),
    end_time: document.getElementById('endTime').value.trim(),
    limit: '20'
  });
  const res = await fetch('/api/messages?' + q.toString());
  const data = await res.json();
  document.getElementById('msgHint').innerHTML = `数据来源：<span class="badge ${data.source === 'redis' ? 'cache':'ok'}">${data.source}</span> TTL: ${data.cache_ttl}s`;
  const tbody = document.getElementById('msgTable');
  tbody.innerHTML = '';
  (data.data || []).forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.id}</td><td>${row.content}</td><td>${row.create_time}</td>`;
    tbody.appendChild(tr);
  });
}

async function createUser() {
  const payload = new URLSearchParams({
    username: document.getElementById('username').value.trim(),
    password: document.getElementById('password').value,
    role: document.getElementById('role').value
  });
  await fetch('/api/users', { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: payload });
  document.getElementById('username').value = '';
  document.getElementById('password').value = '';
  await loadUsers();
}

async function loadUsers() {
  const res = await fetch('/api/users');
  const data = await res.json();
  const tbody = document.getElementById('userTable');
  tbody.innerHTML = '';
  (data.data || []).forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.id}</td><td>${row.username}</td><td>${row.role}</td><td>${row.is_active}</td><td>${row.create_time}</td>`;
    tbody.appendChild(tr);
  });
}

async function loadMetrics() {
  const res = await fetch('/api/metrics');
  const data = await res.json();
  document.getElementById('metricsLine').innerText = `CPU: ${data.current.cpu_load}% | 内存: ${data.current.memory_used_percent}% | 磁盘: ${data.current.disk_used_percent}% | 服务状态: ${data.current.service_status}`;
  const tbody = document.getElementById('monitorTable');
  tbody.innerHTML = '';
  (data.history || []).forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.create_time}</td><td>${row.cpu_load}%</td><td>${row.memory_used_percent}%</td><td>${row.disk_used_percent}%</td><td>${row.service_status}</td>`;
    tbody.appendChild(tr);
  });
}

async function createBackup() {
  const note = document.getElementById('backupNote').value.trim();
  await fetch('/api/backups', { method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body: new URLSearchParams({note}) });
  document.getElementById('backupNote').value = '';
  await loadBackups();
}

async function restoreBackup(id) {
  await fetch(`/api/backups/${id}/restore`, { method:'POST' });
  await loadBackups();
}

async function loadBackups() {
  const res = await fetch('/api/backups');
  const data = await res.json();
  const tbody = document.getElementById('backupTable');
  tbody.innerHTML = '';
  (data.data || []).forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row.id}</td><td>${row.backup_name}</td><td>${row.status}</td><td>${row.create_time}</td><td><button class="primary" onclick="restoreBackup(${row.id})">恢复</button></td>`;
    tbody.appendChild(tr);
  });
}

async function loadLogs() {
  const filename = document.getElementById('logType').value;
  const res = await fetch('/api/logs?filename=' + encodeURIComponent(filename));
  const data = await res.json();
  document.getElementById('logArea').value = (data.lines || []).join('\n');
}

loadMessages(); loadUsers(); loadMetrics(); loadBackups(); loadLogs();
setInterval(loadMetrics, 30000);
</script>
</body>
</html>
    """


# ---------------------- message APIs ----------------------
@app.route("/api/messages", methods=["GET", "POST"])
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
        return jsonify({
            "code": 200,
            "source": "redis",
            "cache_ttl": redis_client.ttl(cache_key),
            "data": json.loads(cache_data),
        })

    rows, safe_limit = list_messages(keyword, start_time, end_time, limit)
    redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(rows, ensure_ascii=False))
    if not keyword and not start_time and not end_time:
        redis_client.setex("hot:messages", CACHE_TTL_SECONDS, json.dumps(rows[:5], ensure_ascii=False))

    return jsonify({
        "code": 200,
        "source": "mysql",
        "cache_ttl": CACHE_TTL_SECONDS,
        "limit": safe_limit,
        "data": rows,
    })


# backward compatibility
@app.route("/add", methods=["POST"])
def add_compat_api():
    return messages_api()


@app.route("/list", methods=["GET"])
def list_compat_api():
    return messages_api()


# ---------------------- health & metrics ----------------------
@app.route("/api/health")
@app.route("/health")
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


@app.route("/api/metrics")
def metrics_api():
    cpu_load = round(os.getloadavg()[0], 2) if hasattr(os, "getloadavg") else 0.0
    mem_used = get_memory_used_percent()
    disk_used = get_disk_used_percent()
    health = health_api().json
    service_status = "ok" if health["mysql"] == "connected" and health["redis"] == "connected" else "degraded"

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO monitor_records (cpu_load, memory_used_percent, disk_used_percent, service_status)
            VALUES (%s, %s, %s, %s)
            """,
            (cpu_load, mem_used, disk_used, service_status),
        )
        cursor.execute(
            """
            SELECT cpu_load, memory_used_percent, disk_used_percent, service_status, create_time
            FROM monitor_records ORDER BY id DESC LIMIT 20
            """
        )
        history = cursor.fetchall()
    conn.commit()
    conn.close()

    history = serialize_datetimes(history)
    current = {
        "cpu_load": cpu_load,
        "memory_used_percent": mem_used,
        "disk_used_percent": disk_used,
        "service_status": service_status,
        "os": platform.platform(),
    }
    redis_client.setex("dashboard:state", CACHE_TTL_SECONDS, json.dumps(current, ensure_ascii=False))

    return jsonify({"code": 200, "current": current, "history": history})


# ---------------------- backups ----------------------
@app.route("/api/backups", methods=["GET", "POST"])
def backups_api():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    if request.method == "POST":
        note = request.form.get("note", "").strip()
        now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{now}.tar.gz"
        backup_path = str(BACKUP_DIR / backup_name)

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO backup_records (backup_name, backup_path, status, note)
                VALUES (%s, %s, %s, %s)
                """,
                (backup_name, backup_path, "created", note),
            )
        conn.commit()
        conn.close()

        with open(backup_path, "w", encoding="utf-8") as f:
            f.write(f"demo backup file created at {datetime.utcnow().isoformat()}\n")

        return jsonify({"code": 200, "msg": "backup created", "backup_name": backup_name})

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT id, backup_name, backup_path, status, note, create_time, restore_time FROM backup_records ORDER BY id DESC"
        )
        rows = cursor.fetchall()
    conn.close()

    return jsonify({"code": 200, "data": serialize_datetimes(rows)})


@app.route("/api/backups/<int:backup_id>/restore", methods=["POST"])
def restore_backup_api(backup_id):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id FROM backup_records WHERE id=%s", (backup_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"code": 404, "msg": "backup not found"}), 404

        cursor.execute(
            "UPDATE backup_records SET status=%s, restore_time=NOW() WHERE id=%s",
            ("restored", backup_id),
        )
    conn.commit()
    conn.close()

    return jsonify({"code": 200, "msg": "restore done", "backup_id": backup_id})


# ---------------------- users ----------------------
@app.route("/api/users", methods=["GET", "POST"])
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
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
                    (username, hash_password(password), role),
                )
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
    redis_client.setex("cache:users", CACHE_TTL_SECONDS, json.dumps(rows, ensure_ascii=False))
    return jsonify({"code": 200, "source": "mysql", "data": rows})


# ---------------------- alerts & logs ----------------------
@app.route("/api/alerts", methods=["GET", "POST"])
def alerts_api():
    if request.method == "POST":
        level = request.form.get("level", "info").strip()
        title = request.form.get("title", "").strip()
        detail = request.form.get("detail", "").strip()
        if not title:
            return jsonify({"code": 400, "msg": "title required"}), 400

        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO alert_records (level, title, detail) VALUES (%s, %s, %s)",
                (level, title, detail),
            )
        conn.commit()
        conn.close()
        return jsonify({"code": 200, "msg": "alert recorded"})

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT id, level, title, detail, create_time FROM alert_records ORDER BY id DESC LIMIT 100")
        rows = cursor.fetchall()
    conn.close()

    return jsonify({"code": 200, "data": serialize_datetimes(rows)})


@app.route("/api/logs")
def logs_api():
    filename = request.args.get("filename", "access.log")
    limit = min(max(int(request.args.get("limit", "200")), 1), 500)
    if filename not in {"access.log", "error.log"}:
        return jsonify({"code": 400, "msg": "filename must be access.log or error.log"}), 400

    lines = read_log_lines(filename, limit)
    return jsonify({"code": 200, "filename": filename, "limit": limit, "lines": lines})


@app.route("/api/stats")
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

    cache_keys = len(list(redis_client.scan_iter("*") ))
    return jsonify(
        {
            "code": 200,
            "db_counts": {
                "messages": message_count,
                "monitor_records": monitor_count,
                "backup_records": backup_count,
                "alert_records": alert_count,
                "users": user_count,
            },
            "redis_keys": cache_keys,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
