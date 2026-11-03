/**
 * Pure helpers for the lesson plan surface.
 *
 * Formatting and download helpers live outside the components so they can be
 * unit-tested without mounting the whole workspace.
 */
import type { LessonPlanPageDocument } from "../../api";
import type { TranslationKey } from "../../i18n";

export const LESSON_PLAN_ACCEPT = ".pdf,.docx,.pptx,.txt,.md,.markdown,.csv,.xlsx,.xls";
export const LESSON_PLAN_MAX_BYTES = 50 * 1024 * 1024;
const ALLOWED_EXTENSIONS = new Set(LESSON_PLAN_ACCEPT.split(","));

/** Map a backend stage token to its copy key. */
export function stageKey(stage: string): TranslationKey {
  const map: Record<string, TranslationKey> = {
    init: "lessonPlan.stage.init",
    collecting: "lessonPlan.stage.collecting",
    ready: "lessonPlan.stage.ready",
    outline: "lessonPlan.stage.outline",
    exported: "lessonPlan.stage.exported",
  };
  return map[stage] ?? "lessonPlan.stage.collecting";
}

/** Read page markdown, keeping a fallback for legacy canvas documents. */
export function documentMarkdown(document: LessonPlanPageDocument | null | undefined): string {
  if (!document) return "";
  if (typeof document.markdown === "string" && document.markdown.trim()) return document.markdown.trim();
  if (Array.isArray(document.elements)) {
    return document.elements
      .map((element) => (element && typeof element.text === "string" ? element.text.trim() : ""))
      .filter(Boolean)
      .join("\n\n");
  }
  return "";
}

/** Validate a material file; returns a copy key for the reason, or null. */
export function materialFileIssue(file: File): "type" | "size" | null {
  const extension = file.name.includes(".") ? `.${file.name.split(".").pop()?.toLowerCase()}` : "";
  if (!ALLOWED_EXTENSIONS.has(extension)) return "type";
  if (file.size <= 0 || file.size > LESSON_PLAN_MAX_BYTES) return "size";
  return null;
}

/** Build a human-friendly download filename. */
export function downloadFilename(title: string, extension: "pdf" | "md"): string {
  const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const clean = title.replace(/[\\/:*?"<>|]+/g, " ").trim().slice(0, 40) || "lesson-plan";
  return `${clean}-${stamp}.${extension}`;
}

/** Trigger a browser download for an in-memory blob. */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Coerce an answers field into a list of display strings. */
export function answerList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean);
  if (typeof value === "string" && value.trim()) return [value.trim()];
  return [];
}

/** Coerce an answers field into a display string. */
export function answerText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value.trim();
  return "";
}

/** Coerce an answers field into a positive number, or null. */
export function answerNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
