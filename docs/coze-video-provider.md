# Coze provider

## 配置

在 `backend/.env` 设置：

```dotenv
COZE_API_BASE_URL=https://api.coze.cn
COZE_API_TOKEN=你的服务端PAT
COZE_WORKFLOW_ID=已发布的workflow id
COZE_BOT_ID=workflow需要关联bot时填写
COZE_TIMEOUT_SECONDS=120
COZE_POLL_INTERVAL_SECONDS=2
COZE_ENABLED=true
```

PAT 在 Coze 控制台的个人访问令牌页面创建。只把 PAT 写入后端环境或密钥管理器；不要放入 `frontend`、浏览器 localStorage、数据库普通字段或提交到 Git。

## Workflow 输入输出

工作流接收 `title`、`course_id`、`learning_objectives`、`audience`、`language`、`duration_seconds`、`style`、`source_text`、`source_materials`、`need_voice`、`need_captions` 和 `need_avatar`。建议输出严格 JSON：

```json
{
  "script": "完整讲稿",
  "scenes": [{"id": "s1", "order": 1, "duration_seconds": 15, "narration": "…", "onscreen_text": "…", "visual_prompt": "…", "caption_text": "…"}],
  "video_url": null,
  "audio_url": null,
  "captions_url": null,
  "render_mode": "local"
}
```

Coze SDK 的 workflow stream 会归一化 `MESSAGE`、`ERROR`、`INTERRUPT` 和完成事件；异步 workflow 使用 `execute_id` 轮询。返回只有脚本/分镜时，任务仍可以交给 Local provider 渲染；返回视频、音频和字幕 URL 时，URL 会保留在统一结果 metadata 中。

如果 JSON 无法解析，任务会失败并保存可读错误；服务端不会把 PAT 写入错误信息。Webhook 扩展点默认关闭，开启后需要 `COZE_WEBHOOK_SECRET` 和签名校验。
