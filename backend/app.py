from flask import Flask, jsonify, request
import redis
import pymysql
import time
from datetime import datetime

app = Flask(__name__)

# ====================== Redis 连接（容器内自动解析） ======================
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True  # 自动转字符串
)

# ====================== MySQL 连接（容器服务名：mysql） ======================
def get_db_connection():
    return pymysql.connect(
        host='mysql',
        user='root',
        password='123456',  # 与你的 docker-compose.yml 保持一致
        database='message_db',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# ====================== 初始化数据库表（首次自动创建） ======================
def init_table():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = '''
            CREATE TABLE IF NOT EXISTS messages (
                id INT PRIMARY KEY AUTO_INCREMENT,
                content TEXT NOT NULL,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            '''
            cursor.execute(sql)
        conn.commit()
        conn.close()
    except Exception as e:
        print("初始化表失败:", e)

# 项目启动时初始化表
init_table()

# ====================== 1. 发布留言接口 ======================
@app.route('/add', methods=['POST'])
def add_message():
    content = request.form.get('content', '').strip()

    # 非空校验
    if not content:
        return jsonify({"code": 400, "msg": "留言内容不能为空"}), 400

    try:
        # 写入 MySQL
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "INSERT INTO messages (content) VALUES (%s)"
            cursor.execute(sql, (content,))
        conn.commit()
        conn.close()

        # 新增后删除缓存（保证下次查询是最新数据）
        redis_client.delete('message_list')

        return jsonify({"code": 200, "msg": "留言发布成功"})

    except Exception as e:
        return jsonify({"code": 500, "msg": "发布失败", "error": str(e)}), 500

# ====================== 2. 查询留言接口（Redis 缓存优先） ======================
@app.route('/list')
def get_messages():
    # 先从 Redis 取
    cache_data = redis_client.get('message_list')

    if cache_data:
        return jsonify({
            "code": 200,
            "source": "redis",
            "data": eval(cache_data)  # 字符串转回列表
        })

    # Redis 没有 → 查 MySQL
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT id, content, create_time FROM messages ORDER BY id DESC"
            cursor.execute(sql)
            messages = cursor.fetchall()
        conn.close()

        # 存入 Redis，缓存 60 秒
        redis_client.setex('message_list', 60, str(messages))

        return jsonify({
            "code": 200,
            "source": "mysql",
            "data": messages
        })

    except Exception as e:
        return jsonify({"code": 500, "msg": "查询失败", "error": str(e)}), 500

# ====================== 3. 首页（展示功能） ======================
@app.route('/')
def index():
    return """
    <h1>留言板系统（Docker + MySQL + Redis）</h1>
    <p>接口说明：</p>
    <p>POST /add  发布留言</p>
    <p>GET  /list 查询留言（缓存60秒）</p>
    <p>GET  /health 健康检查</p>
    """

# ====================== 4. 健康检查 ======================
@app.route('/health')
def health():
    return {
        "status": "ok",
        "redis": "connected",
        "mysql": "connected",
        "time": time.time()
    }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)