/**
 * Workspace sidebar: the living brief, attached materials and export options.
 */
import React from "react";
import type { LessonPlanAsset } from "../../api";
import { useI18n } from "../../i18n";
import { LESSON_PLAN_ACCEPT, answerList, answerNumber, answerText } from "./lessonPlanFormat";

export type LessonPlanSidebarProps = {
  answers: Record<string, unknown>;
  briefSummary: string;
  ready: boolean;
  assets: LessonPlanAsset[];
  hasPages: boolean;
  generating: boolean;
  generateDisabled?: boolean;
  uploading: boolean;
  exporting: boolean;
  format: "pdf" | "markdown";
  includeAnswers: boolean;
  blackWhite: boolean;
  degraded: boolean;
  onGenerate: () => void;
  onUpload: (files: FileList | File[]) => void;
  onDeleteFile: (asset: LessonPlanAsset) => void;
  onFormatChange: (format: "pdf" | "markdown") => void;
  onIncludeAnswersChange: (value: boolean) => void;
  onBlackWhiteChange: (value: boolean) => void;
  onExport: () => void;
};

/** Right-hand rail of the lesson plan workspace. */
export default function LessonPlanSidebar({ answers, briefSummary, ready, assets, hasPages, generating, generateDisabled = false, uploading, exporting, format, includeAnswers, blackWhite, degraded, onGenerate, onUpload, onDeleteFile, onFormatChange, onIncludeAnswersChange, onBlackWhiteChange, onExport }: LessonPlanSidebarProps) {
  const { t } = useI18n();
  const subject = answerText(answers.subject);
  const grade = answerText(answers.grade);
  const duration = answerNumber(answers.duration_minutes);
  const objectives = answerList(answers.objectives);
  const activities = answerList(answers.activities);
  const pageCount = answerNumber(answers.page_count);
  const rows = [
    { key: "subject", label: t("lessonPlan.sidebar.subject"), value: subject },
    { key: "grade", label: t("lessonPlan.sidebar.grade"), value: grade },
    { key: "duration", label: t("lessonPlan.sidebar.duration"), value: duration ? t("lessonPlan.sidebar.minutes", { count: duration }) : "" },
    { key: "objectives", label: t("lessonPlan.sidebar.objectives"), value: objectives.join("；") },
    { key: "activities", label: t("lessonPlan.sidebar.activities"), value: activities.join("；") },
    { key: "pages", label: t("lessonPlan.sidebar.pageCount"), value: pageCount ? String(pageCount) : "" },
  ];

  return (
    <aside className="lesson-sidebar">
      <section className="lesson-side-card">
        <header className="lesson-side-head">
          <div>
            <span className="lesson-eyebrow">BRIEF</span>
            <h2>{t("lessonPlan.sidebar.briefTitle")}</h2>
          </div>
          <span className={`lesson-state-pill ${ready ? "is-ready" : ""}`}>
            <i aria-hidden="true" />{ready ? t("lessonPlan.sidebar.ready") : t("lessonPlan.sidebar.collecting")}
          </span>
        </header>
        <p className={`lesson-brief-summary ${briefSummary ? "" : "is-empty"}`}>{briefSummary || t("lessonPlan.sidebar.briefEmpty")}</p>
        <dl className="lesson-brief-list">
          {rows.map((row) => (
            <div key={row.key} className={row.value ? "" : "is-missing"}>
              <dt>{row.label}</dt>
              <dd>{row.value || t("lessonPlan.sidebar.missing")}</dd>
            </div>
          ))}
        </dl>
        <button type="button" className="lesson-button primary lesson-generate-button" onClick={onGenerate} disabled={generating || generateDisabled}>
          {generating ? t("lessonPlan.sidebar.generating") : hasPages ? t("lessonPlan.sidebar.regenerate") : t("lessonPlan.sidebar.generate")}
        </button>
        {degraded ? <p className="lesson-side-note">{t("lessonPlan.sidebar.degradedNote")}</p> : null}
      </section>

      <section className="lesson-side-card">
        <header className="lesson-side-head">
          <div>
            <span className="lesson-eyebrow">MATERIALS</span>
            <h2>{t("lessonPlan.sidebar.materialsTitle")}</h2>
          </div>
          <strong className="lesson-side-count">{assets.length}</strong>
        </header>
        {assets.length ? (
          <ul className="lesson-material-list">
            {assets.map((asset) => (
              <li key={asset.id}>
                <div>
                  <span className="lesson-material-name" title={asset.title}>{asset.title}</span>
                  <small className={asset.error ? "is-warning" : ""}>
                    {asset.error
                      ? asset.error
                      : t("lessonPlan.sidebar.materialChars", { count: asset.chars }) + (asset.truncated ? t("lessonPlan.sidebar.truncated") : "")}
                  </small>
                </div>
                <button type="button" onClick={() => onDeleteFile(asset)} aria-label={t("lessonPlan.sidebar.removeMaterial", { name: asset.title })}>×</button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="lesson-side-empty">{t("lessonPlan.sidebar.materialsEmpty")}</p>
        )}
        <label className={`lesson-attach lesson-attach-wide ${uploading ? "is-busy" : ""}`}>
          <input
            type="file"
            multiple
            accept={LESSON_PLAN_ACCEPT}
            disabled={uploading}
            onChange={(event) => { onUpload(event.target.files || []); event.currentTarget.value = ""; }}
          />
          <span>+</span> {uploading ? t("lessonPlan.sidebar.uploading") : t("lessonPlan.sidebar.addMaterial")}
        </label>
        <p className="lesson-side-hint">{t("lessonPlan.sidebar.materialHint")}</p>
      </section>

      <section className="lesson-side-card">
        <header className="lesson-side-head">
          <div>
            <span className="lesson-eyebrow">EXPORT</span>
            <h2>{t("lessonPlan.sidebar.exportTitle")}</h2>
          </div>
        </header>
        <div className="lesson-format-toggle" role="group" aria-label={t("lessonPlan.sidebar.formatLabel")}>
          <button type="button" className={format === "pdf" ? "is-active" : ""} onClick={() => onFormatChange("pdf")} disabled={!hasPages}>PDF</button>
          <button type="button" className={format === "markdown" ? "is-active" : ""} onClick={() => onFormatChange("markdown")} disabled={!hasPages}>Markdown</button>
        </div>
        <label className="lesson-checkbox">
          <input type="checkbox" checked={includeAnswers} onChange={(event) => onIncludeAnswersChange(event.target.checked)} />
          <span>{t("lessonPlan.sidebar.includeAnswers")}</span>
        </label>
        <label className={`lesson-checkbox ${format === "markdown" ? "is-disabled" : ""}`}>
          <input type="checkbox" checked={blackWhite} disabled={format === "markdown"} onChange={(event) => onBlackWhiteChange(event.target.checked)} />
          <span>{t("lessonPlan.sidebar.blackWhite")}</span>
        </label>
        <button type="button" className="lesson-button primary lesson-generate-button" onClick={onExport} disabled={!hasPages || exporting}>
          {exporting ? t("lessonPlan.sidebar.exporting") : t("lessonPlan.sidebar.download")}
        </button>
        <p className="lesson-side-hint">{hasPages ? t("lessonPlan.sidebar.exportHint") : t("lessonPlan.sidebar.exportBlocked")}</p>
      </section>
    </aside>
  );
}
