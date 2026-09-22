import React from "react";
import { fileApi, getApiErrorMessage, type ProcessingDocument, type UploadedFile } from "../../api";

export const PROCESSABLE_ACCEPT = ".pdf,.pptx,.docx,.xlsx,.xls,.txt,.md,.markdown,.csv,.json,image/png,image/jpeg,image/webp";

export function ProcessingStatus({ document, onRetry }: { document?: ProcessingDocument | null; onRetry?: () => void }) {
  if (!document) return null;
  const job = document.job;
  const status = document.status === "partial_ready" ? "已完成（PDF 降级解析）" : document.status === "ready" ? "已完成" : document.status === "failed" ? "处理失败" : job?.stage === "extracting" ? `解析中 ${Math.round(job.progress || 0)}%` : "排队中";
  return <span className={`file-processing-status file-processing-${document.status}`} title={document.error_message || undefined}>{status}{document.status === "failed" && onRetry ? <button type="button" onClick={onRetry}>重试</button> : null}</span>;
}

export default function FileUploader({ onUploaded, accept = PROCESSABLE_ACCEPT, multiple = true, disabled = false }: { onUploaded: (items: UploadedFile[]) => void; accept?: string; multiple?: boolean; disabled?: boolean }) {
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const upload = async (files: File[]) => {
    if (!files.length) return;
    setBusy(true); setError(null);
    try {
      const items: UploadedFile[] = [];
      for (const file of files) items.push((await fileApi.upload(file)).data);
      onUploaded(items);
    } catch (e: unknown) { setError(getApiErrorMessage(e, "文件上传失败")); }
    finally { setBusy(false); }
  };
  return <div className="file-uploader"><label className="file-uploader-button">{busy ? "上传中…" : "＋ 添加文件"}<input type="file" accept={accept} multiple={multiple} disabled={disabled || busy} hidden onChange={(event) => { void upload(Array.from(event.target.files || [])); event.currentTarget.value = ""; }} /></label>{error ? <span className="file-uploader-error">{error}</span> : null}</div>;
}
