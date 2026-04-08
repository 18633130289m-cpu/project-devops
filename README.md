# project-devops

这是一个以 **DevOps 全链路演示** 为目标的项目：

- 前端：管理页面、监控面板、备份记录页面、日志查看页面
- 后端：接口服务、健康检查、监控数据接口、备份恢复接口、用户管理接口
- 数据库：存储监控记录、备份记录、告警记录、用户信息
- Redis：缓存热点数据、仪表盘状态、接口查询结果
- 运维层：Docker Compose、部署脚本、监控脚本、备份恢复脚本

---

## 1. 架构总览

```text
Browser
  -> Nginx(:80)
      -> Flask API(:5000)
         -> MySQL (业务与运维记录)
         -> Redis (查询缓存/仪表盘状态/热点数据)
```

---

## 2. 功能映射

### 2.1 前端页面

访问 `http://127.0.0.1/` 后可看到四个页面：

1. **管理页面**
   - 留言发布
   - 留言查询（关键词 + 时间范围）
   - 用户创建与用户列表
2. **监控面板**
   - CPU、内存、磁盘、服务状态
   - 最近监控历史记录
3. **备份记录页面**
   - 创建备份
   - 恢复指定备份
4. **日志查看页面**
   - 查看 `access.log` / `error.log`

### 2.2 后端接口

- `GET/POST /api/messages`：留言发布与查询
- `GET /api/health`：MySQL、Redis 健康检查
- `GET /api/metrics`：采集并返回监控数据
- `GET/POST /api/backups`：备份记录查询/创建
- `POST /api/backups/<id>/restore`：恢复接口
- `GET/POST /api/users`：用户管理接口
- `GET/POST /api/alerts`：告警记录接口
- `GET /api/logs`：日志查看接口
- `GET /api/stats`：数据库记录数量与 Redis key 概览

兼容旧接口：
- `POST /add` -> 转发到 `POST /api/messages`
- `GET /list` -> 转发到 `GET /api/messages`

### 2.3 MySQL 表设计（自动初始化）

- `messages`：留言数据
- `monitor_records`：监控历史记录
- `backup_records`：备份与恢复记录
- `alert_records`：告警记录
- `users`：用户信息

### 2.4 Redis 缓存策略

- `query:messages:*`：留言查询结果缓存
- `hot:messages`：热点留言缓存
- `dashboard:state`：仪表盘状态缓存
- `cache:users`：用户列表缓存

---

## 3. 快速启动

```bash
docker compose up -d --build
```

查看状态：

```bash
docker compose ps
```

---

## 4. 关键使用示例

### 4.1 新增留言

```bash
curl -X POST http://127.0.0.1/api/messages -d "content=第一次留言"
```

### 4.2 条件查询留言

```bash
curl "http://127.0.0.1/api/messages?keyword=留言&start_time=2026-04-01%2000:00:00&end_time=2026-04-30%2023:59:59&limit=20"
```

### 4.3 创建用户

```bash
curl -X POST http://127.0.0.1/api/users \
  -d "username=admin&password=admin123&role=admin"
```

### 4.4 创建备份

```bash
curl -X POST http://127.0.0.1/api/backups -d "note=manual-backup"
```

### 4.5 恢复备份

```bash
curl -X POST http://127.0.0.1/api/backups/1/restore
```

---

## 5. 运维脚本

- `deploy.sh`：容器部署脚本
- `check_container.sh`：容器巡检脚本
- `log_analyze.sh`：日志分析脚本
- `monitor_metrics.sh`：定时采集监控指标并落盘
- `backup_restore.sh`：调用备份/恢复接口

示例：

```bash
bash monitor_metrics.sh
bash backup_restore.sh create "nightly backup"
bash backup_restore.sh restore 1
```

---

## 6. 下一步建议（继续提升含金量）

1. 接入 Prometheus + Grafana，实现真正时序监控与告警规则。
2. 增加 JWT 登录鉴权 + RBAC 权限控制（admin/operator/viewer）。
3. 为备份功能接入真实数据库导出/导入（`mysqldump` + restore）。
4. 增加 CI 流水线（lint/test/build/smoke）。
5. 使用 Ansible 完成多主机自动化部署。
