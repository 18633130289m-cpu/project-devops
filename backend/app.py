from flask import Flask
import redis
import time

app = Flask(__name__)
# 连接Redis容器（服务名就是redis，Docker Compose自动解析）
redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# 首页：访问计数功能
@app.route('/')
def index():
    count = redis_client.incr('visit_count')
    return f"<h1>DevOps 容器平台</h1><p>总访问次数：{count}</p>"

# 健康检查接口
@app.route('/health')
def health():
    return {"status": "ok", "time": time.time()}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
