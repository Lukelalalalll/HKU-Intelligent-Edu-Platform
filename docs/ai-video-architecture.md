# AI 教学视频架构

AI 教学视频是教师侧的独立业务，入口为 `/teacher/ai-video`，后端 API 前缀为 `/api/teacher/video-projects`。项目、来源、场景、生成任务和产物分别持久化在 `video_projects`、`video_sources`、`video_scenes`、`video_generation_jobs` 和 `video_assets` 表中，迁移为 `0018_ai_video`。

生成请求先在同一数据库事务中创建 `VideoGenerationJob` 和 `TaskOutbox`，提交后才交给 Celery/Redis；没有 broker 时沿用集中式 ThreadPool fallback。数据库任务行是恢复和查询的唯一来源，应用启动会重新投递 `queued`、`preparing` 和 `rendering` 任务。API、worker 和前端都只依赖 provider-neutral 的状态、进度、脚本、场景和产物结构。

`CozeProvider` 负责工作流编排和脚本/分镜输出；`LocalProvider` 负责低成本卡片视频 MVP。两者都实现 `validate_config`、`create_generation_job`、`run_generation`、`cancel_generation`、`get_status`、`normalize_event` 和 `health_check`。Coze token 只从服务端环境变量读取，前端、数据库业务字段和普通日志不保存 token。

第一阶段默认交付脚本、旁白轨、VTT/SRT 字幕和 FFmpeg 卡片 MP4。GPT-SoVITS、faster-whisper、Remotion、ComfyUI、LTX-Video、Wan2.1、CogVideo、SadTalker 和 Wav2Lip 都通过本地 worker 或后续可插拔 provider 接入，不在 Web API 进程内运行长时间 GPU 推理。

部署前执行 `cd backend && alembic upgrade head`，启动 Redis/Celery 后运行 `celery -A celery_worker.celery_app worker --loglevel=INFO --pool=solo`。生产环境应把 `VIDEO_STORAGE_DIR` 指向受保护的持久化存储，并通过鉴权下载路由提供产物。
