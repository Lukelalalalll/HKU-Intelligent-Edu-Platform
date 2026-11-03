import React from "react";
import { fileApi, getApiErrorMessage, type ProcessingDocument, type UploadedFile } from "../../api";
import { useI18n } from "../../i18n";

/**
 * File picker filter matching the backend processing whitelist.
 */
export const PROCESSABLE_ACCEPT = ".pdf,.pptx,.docx,.xlsx,.xls,.txt,.md,.markdown,.csv,.json,image/png,image/jpeg,image/webp";

/**
 * Compact processing-state label for an uploaded document.
 */
export function ProcessingStatus({ document, onRetry }: { document?: ProcessingDocument | null; onRetry?: () => void }) {
  const { t } = useI18n();
  if (!document) return null;
  const job = document.job;
  const status = document.status === "partial_ready"
    ? t("shared.fileUploader.status.readyPdfFallback")
    : document.status === "ready"
      ? t("shared.fileUploader.status.ready")
      : document.status === "failed"
        ? t("shared.fileUploader.status.failed")
        : job?.stage === "extracting"
          ? t("shared.fileUploader.status.extracting", { progress: Math.round(job.progress || 0) })
          : t("shared.fileUploader.status.queued");
  return <span className={`file-processing-status file-processing-${document.status}`} title={document.error_message || undefined}>{status}{document.status === "failed" && onRetry ? <button type="button" onClick={onRetry}>{t("shared.fileUploader.retry")}</button> : null}</span>;
}

/**
 * Upload files through the processing pipeline and report the assets.
 */
export default function FileUploader({ onUploaded, accept = PROCESSABLE_ACCEPT, multiple = true, disabled = false }: { onUploaded: (items: UploadedFile[]) => void; accept?: string; multiple?: boolean; disabled?: boolean }) {
  const { t } = useI18n();
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const upload = async (files: File[]) => {
    if (!files.length) return;
    setBusy(true); setError(null);
    try {
      const items: UploadedFile[] = [];
      for (const file of files) items.push((await fileApi.upload(file)).data);
      onUploaded(items);
    } catch (e: unknown) { setError(getApiErrorMessage(e, t("shared.fileUploader.uploadFailed"))); }
    finally { setBusy(false); }
  };
  return <div className="file-uploader"><label className="file-uploader-button">{busy ? t("shared.fileUploader.uploading") : t("shared.fileUploader.addFiles")}<input type="file" accept={accept} multiple={multiple} disabled={disabled || busy} hidden onChange={(event) => { void upload(Array.from(event.target.files || [])); event.currentTarget.value = ""; }} /></label>{error ? <span className="file-uploader-error">{error}</span> : null}</div>;
}
