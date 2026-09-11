# 本地 MinerU PDF/PPTX 预处理平台

面向 Codex 的本地 PDF/PPTX 预处理服务，输出 Markdown、页/幻灯片级 JSON、代码/公式/表格块和可检索 chunk。

## 架构

```text
React/Vite -> FastAPI -> SQLite 任务队列 -> PDF: MinerU/PyMuPDF
                                      -> PPTX: python-pptx
                                      -> pages/blocks/chunks/artifacts
```

## 启动

```powershell
cd D:\Desktop\Pdf-Process\Process\新建文件夹
Copy-Item .env.example .env
.\run.ps1
```

API 文档：`http://localhost:8000/docs`  
前端：`http://localhost:5173`

## 支持格式

- PDF：MinerU 3.4.4 负责版面、表格、公式和 OCR；PyMuPDF 作为原生文本回退。
- PPTX：python-pptx 提取每张幻灯片的标题、文本框、代码样式文本和归一化几何位置。

上传接口 `POST /api/v1/documents` 使用字段 `files`，支持批量 PDF/PPTX。

## 产物

每个文档位于 `data/documents/<id>/`，包括 `manifest.json`、`document.md`、`pages/page-XXX.json`、`chunks.jsonl` 和日志。页面 JSON 保留 block 类型、LaTeX、代码、表格、置信度和 bbox，方便 Codex 精确定位复杂公式、代码和表格。

PDF 优先使用 MinerU；当 pipeline 或模型暂不可用且 PDF 有文本层时，系统自动保存原生文本并在 `manifest.json` 记录降级原因。PPTX 直接使用 python-pptx 解析。

## 公式和代码

公式块以独立 `$$ ... $$` Markdown 输出，并保留原始 `latex` 字段。代码块以 fenced code block 输出，并在 JSON 中标记为 `code`。文本中包含 `def`、`import`、`print`、`pandas`、`numpy`、`plt` 等代码信号时，系统会进行代码块候选识别。
