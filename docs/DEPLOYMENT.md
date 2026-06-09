# 部署说明

本项目是前后端分离系统：

- 前端：`frontend`，Vite + React，构建产物是静态文件。
- 后端：`backend`，FastAPI，提供 `/api/v1` 接口。
- 数据服务：PostgreSQL、Redis、Elasticsearch、MinIO。

## 能否直接部署到 GitHub Pages

不能把完整系统直接部署到 GitHub Pages。GitHub Pages 只适合托管静态站点，不能运行 FastAPI 后端、数据库、Redis、Elasticsearch 或 MinIO。

可行方式是：

1. 前端部署到 GitHub Pages。
2. 后端部署到 Render、Railway、Fly.io、云服务器、Kubernetes 或其他可运行 Python 服务的平台。
3. 前端构建时配置 `VITE_API_BASE_URL=https://你的后端域名/api/v1`。

如果只把前端放到 Pages，但没有线上后端，页面可以打开，登录、题库、考试、规划等依赖 API 的功能会失败。

## 推荐生产部署

### 方案 A：Docker Compose 上云服务器

适合先快速上线完整系统。

1. 准备一台 Linux 云服务器，安装 Docker 和 Docker Compose。
2. 配置域名，例如：
   - 前端：`https://exam.example.com`
   - 后端：`https://api.exam.example.com`
3. 在服务器拉取代码：

```bash
git clone https://github.com/zccztt/self-study-exam-hub.git
cd self-study-exam-hub
```

4. 创建生产 `.env`，至少修改：

```env
APP_ENV=production
DEBUG=false
SECRET_KEY=替换为强随机字符串
FRONTEND_URL=https://exam.example.com
DATABASE_URL=postgresql://exam_user:强密码@postgres:5432/exam_hub
REDIS_URL=redis://redis:6379/0
ELASTICSEARCH_URL=http://elasticsearch:9200
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=替换为生产账号
MINIO_SECRET_KEY=替换为生产密码
```

5. 启动服务：

```bash
docker compose up -d --build
docker compose exec backend python backend/init_db.py
```

6. 用 Nginx/Caddy 做 HTTPS 反向代理：
   - `/api/` 转发到后端 `8000`
   - 前端可用 Nginx 托管 `frontend/dist`，或继续由容器提供

当前 `frontend/Dockerfile` 使用的是开发服务器，生产环境建议改为构建静态文件后由 Nginx 托管。

### 方案 B：前端 GitHub Pages + 后端托管平台

适合已有 GitHub 仓库并希望前端自动发布。

1. 将后端部署到可运行 FastAPI 的平台。
2. 确保后端允许前端域名跨域：

```env
DEBUG=false
FRONTEND_URL=https://zccztt.github.io
```

如果 Pages 地址是项目页，常见地址是：

```text
https://zccztt.github.io/self-study-exam-hub/
```

3. 在 GitHub 仓库设置 Secrets：

```text
VITE_API_BASE_URL=https://你的后端域名/api/v1
```

4. 启用 GitHub Pages：
   - Settings -> Pages
   - Source 选择 GitHub Actions

5. 推送到 `main` 后，`.github/workflows/deploy-pages.yml` 会自动构建并发布前端。

## 本地验证生产构建

```bash
cd frontend
npm install
npm run build
npm run preview
```

如果部署到 GitHub Pages 项目页，本地模拟仓库子路径：

```bash
cd frontend
$env:VITE_APP_BASE='/self-study-exam-hub/'
$env:VITE_API_BASE_URL='https://你的后端域名/api/v1'
npm run build
```

## 上线检查清单

- `SECRET_KEY` 已替换，不能使用默认值。
- `DEBUG=false`。
- `FRONTEND_URL` 是线上前端域名。
- 数据库、Redis、MinIO 密码已替换。
- 后端 HTTPS 可访问 `/api/v1/health`。
- 前端构建时 `VITE_API_BASE_URL` 指向线上后端。
- 数据库已初始化：`python backend/init_db.py`。
