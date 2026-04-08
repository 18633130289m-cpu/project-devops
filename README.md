# project-devops

一个基于 **Docker Compose + Flask + MySQL + Redis + Nginx** 的 DevOps 练习项目。该项目实现了一个简易留言板服务，并配套了部署与巡检脚本，适合用于学习容器化部署、服务编排和基础运维自动化。

---

## 1. 项目架构

- **Nginx**：统一入口，反向代理到 Flask 后端。
- **Flask Backend**：提供留言发布、列表查询、健康检查接口。
- **MySQL**：持久化存储留言数据。
- **Redis**：缓存留言列表（60 秒）以降低数据库读取压力。

请求链路：

```text
Client -> Nginx(:80) -> Flask(:5000) -> MySQL
                           |
                           +-> Redis (缓存)
```

---

## 2. 目录结构

```text
project-devops/
├── compose.yml              # 容器编排文件
├── init_mysql.sql           # MySQL 初始化脚本（建库/建用户/授权）
├── deploy.sh                # 一键部署脚本
├── check_container.sh       # 容器巡检与自动重启脚本
├── log_analyze.sh           # 监控/日志分析/备份脚本
├── backend/
│   ├── Dockerfile           # Flask 镜像构建
│   └── app.py               # 应用代码
├── nginx/
│   ├── Dockerfile           # Nginx 镜像构建
│   └── nginx.conf           # 反向代理配置
├── logs/
│   ├── access.log           # 示例访问日志
│   └── error.log            # 错误日志
└── ansible/
    └── deploy.yml           # 预留：Ansible 自动化部署剧本（待补充）
```

---

## 3. 环境要求

- Linux / macOS（推荐 Linux）
- Docker >= 20.x
- Docker Compose v2（`docker compose` 子命令）

> 说明：项目内 `deploy.sh` 已尝试自动安装 Docker 与 Compose，但在不同发行版上建议手动确认安装情况。

---

## 4. 快速开始

### 4.1 克隆项目

```bash
git clone <your-repo-url>
cd project-devops
```

### 4.2 启动服务

```bash
docker compose up -d --build
```

### 4.3 查看运行状态

```bash
docker compose ps
```

### 4.4 访问首页

- 浏览器访问：`http://<服务器IP>/`
- 本机开发：`http://127.0.0.1/`

---

## 5. 接口文档

后端默认通过 Nginx 暴露（80 端口）。

### 5.1 发布留言

- **URL**：`POST /add`
- **Content-Type**：`application/x-www-form-urlencoded`
- **参数**：
  - `content`（string，必填）

示例：

```bash
curl -X POST http://127.0.0.1/add \
  -d "content=你好，DevOps"
```

成功响应：

```json
{"code":200,"msg":"Successful"}
```

失败响应（空内容）：

```json
{"code":400,"msg":"Empty"}
```

### 5.2 查询留言

- **URL**：`GET /list`
- **说明**：优先走 Redis 缓存，缓存 TTL 为 60 秒。

示例：

```bash
curl http://127.0.0.1/list
```

响应示例：

```json
{
  "code": 200,
  "source": "redis",
  "data": [
    {
      "id": 1,
      "content": "你好，DevOps",
      "create_time": "2026-03-20 12:00:00"
    }
  ]
}
```

### 5.3 健康检查

- **URL**：`GET /health`
- **说明**：返回 MySQL 与 Redis 连接状态。

示例：

```bash
curl http://127.0.0.1/health
```

响应示例：

```json
{
  "mysql": "connected",
  "redis": "connected"
}
```

---

## 6. 数据与持久化

`compose.yml` 中定义了两个命名卷：

- `mysql-data`：持久化 MySQL 数据
- `redis-data`：持久化 Redis 数据

MySQL 首次启动时会执行 `init_mysql.sql`：

1. 创建 `message_db`
2. 创建用户 `flask_user`
3. 授权 `message_db.*`

---

## 7. 运维脚本说明

### 7.1 一键部署脚本

```bash
bash deploy.sh
```

功能：

- 检查 Docker
- 检查 Docker Compose
- 重建并启动所有服务
- 输出容器状态与访问地址

### 7.2 容器巡检脚本

```bash
bash check_container.sh
```

功能：

- 检查核心容器是否运行
- 异常时自动执行 `docker start`
- 追加巡检记录到 `check_log.txt`

可配合 `crontab` 使用（每 5 分钟巡检一次）：

```cron
*/5 * * * * /bin/bash /path/to/project-devops/check_container.sh
```

### 7.3 日志分析与备份脚本

```bash
bash log_analyze.sh
```

功能：

- 主机 ping 检测
- 端口探测
- CPU / 内存 / 磁盘阈值告警
- 日志关键字分析
- 日志清理
- 目录备份
- 邮件告警

> 使用前请先修改脚本中的路径、邮箱与阈值参数。

---

## 8. 常见问题（FAQ）

### Q1：容器启动失败怎么办？

1. `docker compose ps` 查看容器状态。
2. `docker compose logs -f backend` 查看后端日志。
3. `docker compose logs -f mysql` 检查数据库初始化是否成功。

### Q2：`/list` 接口没有最新数据？

- 该接口有 60 秒缓存。
- 新增留言后后端会删除 `message_list` 缓存 key，一般可立即看到新数据。

### Q3：访问 `http://IP/` 失败？

1. 检查服务器防火墙与安全组是否放行 80 端口。
2. 检查 Nginx 容器是否运行。
3. 检查 backend 容器是否健康。

---

## 9. 安全与生产建议

当前项目偏学习演示用途，生产前建议至少完成：

1. 将数据库密码等敏感信息移入 `.env` 或 Secret 管理。
2. Flask 关闭 `debug=True`，改用 Gunicorn/Uvicorn 等生产服务。
3. 为各容器增加 `healthcheck` 与资源限制（CPU/内存）。
4. 增加 CI/CD、镜像扫描、日志采集与监控告警。

---

## 10. 后续规划

- [ ] 完成 `ansible/deploy.yml` 自动化部署剧本
- [ ] 增加 `.env` 与多环境配置（dev/test/prod）
- [ ] 完善单元测试与接口测试
- [ ] 引入 Prometheus + Grafana 基础监控

---

## 11. License

如无特别说明，默认仅用于学习和内部演示，请按你的团队规范补充正式许可证。
