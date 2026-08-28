# HKU Intelligent Edu Platform

前后端分离的智能教学平台 Phase 1。当前版本提供三角色登录、统一工作台、课程/选课/作业基础链路，以及面向教材课件和未来 RAG/录课能力的数据库扩展结构。

## 技术栈

- Frontend: React 18、TypeScript、Vite、React Router、Zustand、Axios
- Backend: FastAPI、SQLAlchemy 2、Alembic、PostgreSQL
- Auth: HttpOnly Cookie JWT（access/refresh）
- Storage: `backend/uploads/` 本地磁盘，数据库保存文件元数据

## 环境要求

- Python 3.11+
- Node.js 18+
- Docker Desktop

## 快速启动

### 1. 启动 PostgreSQL

```powershell
docker compose up -d postgres
```

### 2. 初始化后端环境

```powershell
python -m venv backend/venv
.\backend\venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
```

迁移并创建演示数据：

```powershell
cd backend
alembic upgrade head
python -m app.seed
```

启动 API：

```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：<http://localhost:8000/docs>

### 3. 启动前端

新开终端：

```powershell
cd frontend
npm install
npm run dev
```

访问 <http://localhost:5173>。

## 演示账户

密码统一为 `123456`：

| 角色 | 用户名 | 邮箱 |
| --- | --- | --- |
| student | `demo_student` | `demo_student@example.test` |
| teacher | `demo_teacher` | `demo_teacher@example.test` |
| admin | `demo_admin` | `demo_admin@example.test` |

登录页在开发模式提供快捷填充按钮，但仍然调用真实登录 API。

## 目录结构

```text
backend/
  app/main.py              # FastAPI 入口
  app/api/routes/          # auth、courses、assignments、files
  app/models/              # 用户、课程、作业、提交、文件、录课、RAG 会话、审计模型
  app/storage/             # 本地存储实现
  alembic/                 # 数据库迁移
frontend/
  src/App.tsx              # 路由、认证页、统一应用壳层
  src/store.ts             # Zustand 认证状态
  src/styles.css           # 登录页与统一工作台样式
```

`reference_projects/` 仅作为设计与业务参考，已加入 `.gitignore`，新项目不会从该目录导入代码。

## Phase 1 已提供的 API

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/session`
- `GET /api/auth/me`
- `GET/POST /api/courses`
- `GET /api/courses/{course_id}`
- `POST/DELETE /api/courses/{course_id}/enroll`
- `GET/POST /api/courses/{course_id}/assignments`
- `POST/GET /api/courses/{course_id}/assignments/{assignment_id}/submissions`
- `POST /api/files`

## 后续 Phase 2

文件中心、课程资料上传界面、RAG 索引和检索、Zoom 录课 API、PPT/Markdown/PDF 处理、评分工作台、通知和生产部署配置。

