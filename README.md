# HKU Intelligent Edu Platform

前后端分离的智能教学平台 Phase 1。当前版本提供三角色登录、统一工作台、课程/选课/作业基础链路，以及面向教材课件和未来 RAG/录课能力的数据库扩展结构。

## 技术栈

- Frontend: React 18、TypeScript、Vite、React Router、Zustand、Axios
- Backend: FastAPI、SQLAlchemy 2、Alembic、PostgreSQL
- Auth: HttpOnly Cookie JWT（access/refresh）
- Storage: `backend/uploads/` 与 `backend/ppt_storage/` 本地磁盘，数据库保存文件元数据

## 环境要求

- Python 3.11+
- Node.js 18+
- Docker Desktop
- （视觉研究）可访问 Bing/Openverse/Wikimedia 的网络出口；大陆开发建议配置本机 HTTP 代理

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

如果需要测试课件 Agent 的浏览器图片采集，还要安装 Playwright 浏览器：

```powershell
python -m pip install playwright
python -m playwright install chromium
```

> 如果当前网络无法下载 Python 包或 Chromium，请先让终端使用可访问外网的代理，再重复执行上面两条命令。Playwright 安装失败时，视觉研究仍会继续尝试 Openverse 和 Wikimedia fallback，但 Bing 浏览器采集不可用。

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
- `GET /api/student/dashboard`
- `GET/PATCH /api/profile`
- `POST/DELETE /api/profile/avatar`
- `PUT /api/profile/password`
- `GET/POST /api/courses`
- `GET /api/courses/{course_id}`
- `POST/DELETE /api/courses/{course_id}/enroll`
- `GET/POST /api/courses/{course_id}/assignments`
- `POST/GET /api/courses/{course_id}/assignments/{assignment_id}/submissions`
- `POST /api/files`
- `GET /api/courses/{course_id}/materials?kind=lecture|tutorial`
- `POST/PATCH/DELETE /api/courses/{course_id}/materials/chapters...`
- `POST/DELETE /api/courses/{course_id}/materials/.../files`
- `GET /api/courses/{course_id}/materials/{material_id}/download`
- `GET/POST /api/courses/{course_id}/live-class`
- `POST /api/courses/{course_id}/live-class/provision`
- `POST /api/courses/{course_id}/live-class/authorize`
- `POST /api/zoom/webhooks`

## 后续 Phase 2

文件中心、课程资料上传界面、RAG 索引和检索、Zoom 录课 API、PPT/Markdown/PDF 处理、评分工作台、通知和生产部署配置。

## 课件 Agent

教师登录后打开 `/teacher/courseware-agent`。在“模型设置”中配置 OpenAI-compatible Base URL、API Key 和模型（默认模板为 DeepSeek：`https://api.deepseek.com` + `deepseek-v4-flash`；可选 `deepseek-v4-pro`、支持图片输入的 `deepseek-v4-flash-vision-exp`）；DeepSeek 暂不提供 Embedding，相关字段可留空。Key 会按教师加密保存并以掩码形式展示。随后可以创建课件项目，上传 PDF/PPTX/DOCX/Markdown 资料，生成大纲、逐页 Summary/Draft/Design，使用 Storyboard 和放映模式预览，并导出可编辑 PPTX。

联网研究优先使用 DeepSeek Responses API 原生的 `web_search` 工具：保持 Base URL 为 `https://api.deepseek.com`，课件 Agent 会在 `/responses` 请求中传入 `tools: [{"type":"web_search"}]`，并将模型返回的来源写入页面素材池。

### 视觉研究图片采集

视觉研究页面使用“左侧 Outline + 右侧候选图片网格”。每页最多保留 6 张候选图片，图片在教师确认选择之前不会自动进入 PPT 排版。采集顺序是：

1. Playwright 打开 Bing Images，提取图片地址、缩略图、来源页、标题和来源说明；
2. 将图片下载到 `backend/ppt_storage/{project_id}/assets/`，记录来源、许可证、搜索词、抓取时间、MIME、宽高和本地 `public_url`；
3. 浏览器搜索失败或无结果时，分别尝试 Openverse 和 Wikimedia Commons；
4. 单页失败不会中断其他页面，任务状态会显示 `completed_with_errors`。

后端默认使用独立的无头 Chromium worker，不依赖教师已经打开的 Chrome。大陆开发时，先启动代理软件，再在 `backend/.env` 中填写代理的 HTTP 地址：

```dotenv
VISUAL_SEARCH_MODE=browser_worker
VISUAL_SEARCH_ENGINE=bing
VISUAL_SEARCH_PROXY=http://127.0.0.1:7890
VISUAL_SEARCH_BROWSER_HEADLESS=true
VISUAL_SEARCH_TIMEOUT_SECONDS=15
VISUAL_SEARCH_MAX_IMAGE_BYTES=8388608
VISUAL_SEARCH_MAX_CONCURRENCY=3
```

`7890` 只是常见示例端口，请替换成代理软件实际的 HTTP 端口。也可以使用环境变量临时覆盖：

```powershell
$env:VISUAL_SEARCH_PROXY = "http://127.0.0.1:7890"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

开发时如果希望使用当前 Chrome/VPN 的代理路径，可改成：

```dotenv
VISUAL_SEARCH_MODE=browser_assisted
VISUAL_SEARCH_PROXY=http://127.0.0.1:7890
```

应用不会保存浏览器 Cookie、账号密码或用户隐私数据，也不会执行图片搜索页面中的脚本指令。图片下载只允许 `http/https`，会拒绝 `localhost`、回环地址和内网 IP。

生产部署使用 `browser_worker`，在服务端安装 Chromium 并配置服务端代理；不需要教师电脑保持 Chrome 窗口打开。若无法安装 Playwright，系统仍保留 Openverse/Wikimedia fallback，但图片覆盖率和地区可用性会降低。

相关配置字段：

| 配置 | 默认值 | 说明 |
| --- | --- | --- |
| `VISUAL_SEARCH_MODE` | `browser_worker` | `browser_worker` 或 `browser_assisted` |
| `VISUAL_SEARCH_ENGINE` | `bing` | 当前浏览器搜索引擎 |
| `VISUAL_SEARCH_PROXY` | 空 | HTTP 代理，例如 `http://127.0.0.1:7890` |
| `VISUAL_SEARCH_TIMEOUT_SECONDS` | `15` | 页面和下载超时 |
| `VISUAL_SEARCH_MAX_IMAGE_BYTES` | `8388608` | 单图大小上限 |
| `VISUAL_SEARCH_MAX_CONCURRENCY` | `3` | 项目任务的全局并发上限 |
| `VISUAL_SEARCH_BROWSER_HEADLESS` | `true` | 是否无头运行 Chromium |
| `VISUAL_SEARCH_BROWSER_EXECUTABLE_PATH` | 空 | 自定义 Chromium/Chrome 路径，可选 |

视觉选择接口保持兼容：`PUT /api/ppt/projects/{project_id}/pages/{page_id}/visual-selection`。`asset_ids` 可以是空数组，表示该页确认使用 0 张图片；只有确认后的 ID 才会进入视觉版式计划。

升级已有数据库时请执行：`cd backend && alembic upgrade head`。

## Zoom 实时课堂

课程详情页支持按排课时间进入嵌入式 Zoom Meeting SDK。教师先点击“准备 Zoom 课堂”，平台会为每条排课创建或同步一个周循环会议；开放时间为课前 15 分钟至课后 30 分钟。需要在 `backend/.env` 配置 Zoom Server-to-Server OAuth、Meeting SDK 和 Webhook 凭据（字段见 `.env.example`）。未配置凭据时，页面会安全地显示待配置状态，不会向浏览器暴露 Zoom Secret 或主持人启动链接。
