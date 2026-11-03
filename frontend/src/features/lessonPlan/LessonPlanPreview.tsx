/**
 * A4 preview of one generated lesson plan page with page-level actions.
 */
import React, { useEffect, useRef, useState } from "react";
import type { LessonPlanPage } from "../../api";
import { useI18n } from "../../i18n";
import { Markdown } from "../../shared/components/Markdown";

const SHEET_WIDTH = 794;
const SHEET_HEIGHT = 1123;

export type LessonPlanPreviewProps = {
  projectTitle: string;
  subject: string;
  grade: string;
  duration: number | null;
  pages: LessonPlanPage[];
  selectedId: string | null;
  hideAnswers: boolean;
  rewriting: boolean;
  generating: boolean;
  onSelect: (pageId: string) => void;
  onEdit: (page: LessonPlanPage) => void;
  onRewrite: (page: LessonPlanPage) => void;
  onGenerate: () => void;
};

/** Paper preview surface with prev/next navigation and page actions. */
export default function LessonPlanPreview({ projectTitle, subject, grade, duration, pages, selectedId, hideAnswers, rewriting, generating, onSelect, onEdit, onRewrite, onGenerate }: LessonPlanPreviewProps) {
  const { t } = useI18n();
  const frameRef = useRef<HTMLDivElement | null>(null);
  const sheetRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);
  const [sheetHeight, setSheetHeight] = useState(SHEET_HEIGHT);
  const index = Math.max(0, pages.findIndex((page) => page.id === selectedId));
  const page = pages[index] ?? null;

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) return;
    const update = () => setScale(Math.min(1, Math.max(0.42, (frame.clientWidth - 48) / SHEET_WIDTH)));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(frame);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const sheet = sheetRef.current;
    if (!sheet) return;
    const update = () => setSheetHeight(Math.max(SHEET_HEIGHT, sheet.scrollHeight));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(sheet);
    return () => observer.disconnect();
  }, [page?.id, hideAnswers]);

  if (!pages.length || !page) {
    return (
      <div className="lesson-preview-empty">
        <div className="lesson-spark" aria-hidden="true">✦</div>
        <h3>{t("lessonPlan.preview.emptyTitle")}</h3>
        <p>{t("lessonPlan.preview.emptyBody")}</p>
        <button type="button" className="lesson-button primary" onClick={onGenerate} disabled={generating}>
          {generating ? t("lessonPlan.preview.generating") : t("lessonPlan.preview.generate")}
        </button>
      </div>
    );
  }

  const metaBits = [subject, grade, duration ? t("lessonPlan.preview.durationMinutes", { count: duration }) : ""].filter(Boolean).join(" · ");

  return (
    <div className="lesson-preview">
      <div className="lesson-preview-toolbar">
        <div className="lesson-preview-nav">
          <button type="button" onClick={() => onSelect(pages[Math.max(0, index - 1)].id)} disabled={index === 0} aria-label={t("lessonPlan.preview.previousPage")}>←</button>
          <span>{t("lessonPlan.preview.pageOf", { current: index + 1, total: pages.length })}</span>
          <button type="button" onClick={() => onSelect(pages[Math.min(pages.length - 1, index + 1)].id)} disabled={index >= pages.length - 1} aria-label={t("lessonPlan.preview.nextPage")}>→</button>
        </div>
        <div className="lesson-preview-actions">
          <button type="button" className="lesson-button secondary" onClick={() => onEdit(page)}>{t("lessonPlan.preview.editPage")}</button>
          <button type="button" className="lesson-button secondary" onClick={() => onRewrite(page)} disabled={rewriting}>
            {rewriting ? t("lessonPlan.preview.rewriting") : t("lessonPlan.preview.rewritePage")}
          </button>
        </div>
      </div>

      <div className="lesson-preview-frame" ref={frameRef}>
        <div className="lesson-sheet-scaler" style={{ width: Math.ceil(SHEET_WIDTH * scale), height: Math.ceil(sheetHeight * scale) }}>
          <div className="lesson-sheet" ref={sheetRef} style={{ width: SHEET_WIDTH, transform: `scale(${scale})` }}>
            <header className="lesson-sheet-head">
              <div>
                <span className="lesson-sheet-eyebrow">HKU · LESSON PLAN</span>
                <h2>{page.title || t("lessonPlan.preview.untitledPage")}</h2>
                <p>{projectTitle}</p>
              </div>
              <div className="lesson-sheet-meta">
                {metaBits ? <span>{metaBits}</span> : null}
                <span>{t("lessonPlan.preview.pageOf", { current: index + 1, total: pages.length })}</span>
              </div>
            </header>
            <div className="lesson-sheet-body">
              <Markdown text={page.markdown} hideAnswers={hideAnswers} />
            </div>
            <footer className="lesson-sheet-foot">
              <span>{t("lessonPlan.preview.footerLabel")}</span>
              <span>{index + 1} / {pages.length}</span>
            </footer>
          </div>
        </div>
      </div>
    </div>
  );
}
