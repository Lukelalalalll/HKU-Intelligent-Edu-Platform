/**
 * Copy shared by reusable UI building blocks (uploaders, status chips…).
 * English is the canonical key shape; keep translations in sync.
 */
const en = {
  fileUploader: {
    addFiles: "＋ Add files",
    uploading: "Uploading…",
    uploadFailed: "File upload failed",
    retry: "Retry",
    status: {
      ready: "Processed",
      readyPdfFallback: "Processed (PDF fallback)",
      failed: "Processing failed",
      extracting: "Parsing {progress}%",
      queued: "Queued",
    },
  },
};

export type SharedMessages = typeof en;

const zhHans: SharedMessages = {
  fileUploader: {
    addFiles: "＋ 添加文件",
    uploading: "上传中…",
    uploadFailed: "文件上传失败",
    retry: "重试",
    status: {
      ready: "已完成",
      readyPdfFallback: "已完成（PDF 降级解析）",
      failed: "处理失败",
      extracting: "解析中 {progress}%",
      queued: "排队中",
    },
  },
};

const yue: SharedMessages = {
  fileUploader: {
    addFiles: "＋ 加入檔案",
    uploading: "上傳緊…",
    uploadFailed: "檔案上傳失敗",
    retry: "重試",
    status: {
      ready: "已完成",
      readyPdfFallback: "已完成（PDF 降級解析）",
      failed: "處理失敗",
      extracting: "解析緊 {progress}%",
      queued: "排緊隊",
    },
  },
};

/** Shared-component copy bundle, one entry per supported locale. */
export const shared = { en, "zh-Hans": zhHans, yue };
