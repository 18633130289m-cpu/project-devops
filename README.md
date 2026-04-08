# project-devops

当前版本采用**前后端分离 + Vue 工程化前端**：

- 前端：Vue3 + Vite + Vue Router + Pinia（`frontend`）
- 后端：Flask API（`backend`）
- 网关：Nginx 统一入口（`nginx`）
- 数据：MySQL + Redis

## 架构

```text
Browser
  -> Nginx(:80)
      -> /           -> frontend(:80, Vue dist)
      -> /api/*      -> backend(:5000, Flask API)
      -> /health     -> backend(:5000)
      -> /add,/list  -> backend(:5000, 兼容旧接口)
```

## 前端工程结构（标准化）

```text
frontend/
  package.json
  vite.config.js
  src/
    main.js
    App.vue
    styles.css
    api/
      http.js
      devops.js
    router/
      index.js
    stores/
      app.js
    components/
      PanelCard.vue
    views/
      ManageView.vue
      MonitorView.vue
      BackupView.vue
      LogsView.vue
```

## 页面能力

- 管理页面：留言发布/查询、用户创建/查询
- 监控面板：指标采集、健康检查、历史监控记录
- 备份记录页面：创建备份、恢复备份
- 日志查看页面：读取 access.log / error.log

## 后端接口

- `GET/POST /api/messages`
- `GET/POST /api/users`
- `GET /api/health`
- `GET /api/metrics`
- `GET/POST /api/backups`
- `POST /api/backups/<id>/restore`
- `GET/POST /api/alerts`
- `GET /api/logs`
- `GET /api/stats`
- 兼容：`POST /add`、`GET /list`

## 启动

```bash
docker compose up -d --build
docker compose ps
```

浏览器访问：`http://127.0.0.1/`

## 本地前端开发（可选）

```bash
cd frontend
npm install
npm run dev
```

## 接口验证

```bash
curl -X POST http://127.0.0.1/api/messages -d "content=hello"
curl "http://127.0.0.1/api/messages?keyword=hello&limit=10"
curl http://127.0.0.1/api/health
```
