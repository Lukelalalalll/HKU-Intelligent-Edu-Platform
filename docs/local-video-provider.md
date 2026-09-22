# Local provider 与 5070 Ti

Local provider 的第一版不要求扩散模型：它把脚本/分镜写入统一结果，使用可选的本地 TTS 命令生成 WAV，再用 FFmpeg 合成卡片 MP4、VTT、SRT 和脚本文件。TTS 命令通过 `LOCAL_VIDEO_TTS_COMMAND` 配置，命令最后接收 UTF-8 文本文件和 WAV 输出路径，因此 GPT-SoVITS、Piper 或校内服务都可以替换。

```dotenv
LOCAL_VIDEO_ENABLED=true
LOCAL_VIDEO_MODEL_DIR=/models/video
LOCAL_VIDEO_MAX_CONCURRENCY=1
LOCAL_VIDEO_WIDTH=1280
LOCAL_VIDEO_HEIGHT=720
LOCAL_VIDEO_FPS=24
LOCAL_VIDEO_STEPS=20
LOCAL_VIDEO_TTS_COMMAND=
```

`GET /api/teacher/video-projects/providers/health` 会报告 CUDA、FFmpeg 和配置状态。启动本地 worker 前检查 `python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"`，不要把显存大小写死。5070 Ti 的分辨率、帧数、采样步数和并发应从环境变量调低，扩散模型只生成短片段再合成。

需要用户另行下载的权重包括 GPT-SoVITS、faster-whisper、LTX-Video/Wan2.1/CogVideo、ComfyUI 工作流模型，以及可选 SadTalker/Wav2Lip 权重；这些权重不提交到 Git。请分别遵守各项目许可证：ComfyUI 为 GPL-3.0，LTX-Video、Wan2.1、CogVideo、Open-Sora 多为 Apache-2.0，GPT-SoVITS 与 faster-whisper 为 MIT，SadTalker/Wav2Lip/Remotion 需按其仓库许可审查商业使用限制。

取消、重试和恢复都通过持久化 job；GPU 推理应放在 Celery 或独立 local worker，不要在 FastAPI route 中创建新的 executor。
