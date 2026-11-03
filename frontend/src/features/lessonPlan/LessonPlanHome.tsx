/**
 * Lesson plan landing page: describe a class, attach materials and reopen work.
 */
import React, { useRef, useState } from "react";
import toast from "react-hot-toast";
import type { LessonPlanCapabilities, LessonPlanProject } from "../../api";
import { useI18n, type TranslationKey } from "../../i18n";
import { LESSON_PLAN_ACCEPT, materialFileIssue } from "./lessonPlanFormat";

export type LessonPlanHomeProps = {
  projects: LessonPlanProject[];
  loading: boolean;
  error: boolean;
  creating: boolean;
  capabilities: LessonPlanCapabilities | null;
  onRetry: () => void;
  onCreate: (text: string, files: File[]) => void;
  onOpen: (project: LessonPlanProject) => void;
  onDelete: (project: LessonPlanProject) => void;
};

const QUICK_STARTS: { label: TranslationKey; prompt: TranslationKey }[] = [
  { label: "lessonPlan.home.quickStarts.foundations", prompt: "lessonPlan.home.quickStartPrompts.foundations" },
  { label: "lessonPlan.home.quickStarts.exam", prompt: "lessonPlan.home.quickStartPrompts.exam" },
  { label: "lessonPlan.home.quickStarts.project", prompt: "lessonPlan.home.quickStartPrompts.project" },
];

/** Landing surface for the lesson plan agent. */
export default function LessonPlanHome({ projects, loading, error, creating, capabilities, onRetry, onCreate, onOpen, onDelete }: LessonPlanHomeProps) {
  const { t, formatDate } = useI18n();
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const addFiles = (incoming: FileList | File[] | null) => {
    if (!incoming) return;
    const accepted: File[] = [];
    for (const file of Array.from(incoming)) {
      const issue = materialFileIssue(file);
      if (issue === "type") toast.error(t("lessonPlan.toast.unsupportedFile", { name: file.name }));
      else if (issue === "size") toast.error(t("lessonPlan.toast.fileTooLarge", { name: file.name }));
      else accepted.push(file);
    }
    if (accepted.length) setFiles((current) => [...current, ...accepted]);
  };

  const removeFile = (index: number) => setFiles((current) => current.filter((_, currentIndex) => currentIndex !== index));

  const submit = () => {
    if (creating || (!prompt.trim() && !files.length)) return;
    onCreate(prompt.trim(), files);
  };

  const fillQuickStart = (key: TranslationKey) => {
    setPrompt(t(key));
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  return (
    <main className="lesson-home">
      <header className="lesson-home-head">
        <div>
          <span className="lesson-eyebrow">LESSON PLAN AGENT</span>
          <h1>
            {t("lessonPlan.home.titleLead")}
            <em>{t("lessonPlan.home.titleAccent")}</em>
          </h1>
          <p>{t("lessonPlan.home.subtitle")}</p>
        </div>
        <div className={`lesson-model-chip ${capabilities?.ai_configured ? "is-ready" : "is-fallback"}`}>
          <i aria-hidden="true" />
          <div>
            <strong>{capabilities?.ai_configured ? t("lessonPlan.home.aiReady") : t("lessonPlan.home.aiFallback")}</strong>
            <small>{capabilities?.ai_configured ? t("lessonPlan.home.aiReadyHint", { model: capabilities?.model || "" }) : t("lessonPlan.home.aiFallbackHint")}</small>
          </div>
        </div>
      </header>

      <div className="lesson-home-grid">
        <section
          className={`lesson-create-card ${dragging ? "is-dragging" : ""}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            addFiles(event.dataTransfer.files);
          }}
        >
          <label className="lesson-composer-label" htmlFor="lesson-plan-brief">{t("lessonPlan.home.composerLabel")}</label>
          <textarea
            id="lesson-plan-brief"
            ref={inputRef}
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder={t("lessonPlan.home.promptPlaceholder")}
            rows={5}
          />

          {files.length ? (
            <ul className="lesson-file-chips">
              {files.map((file, index) => (
                <li key={`${file.name}-${file.size}-${index}`}>
                  <span>{file.name}</span>
                  <button type="button" onClick={() => removeFile(index)} aria-label={t("lessonPlan.home.removeFile", { name: file.name })}>×</button>
                </li>
              ))}
            </ul>
          ) : null}

          <div className="lesson-composer-footer">
            <label className="lesson-attach">
              <input
                type="file"
                multiple
                accept={LESSON_PLAN_ACCEPT}
                onChange={(event) => { addFiles(event.target.files); event.currentTarget.value = ""; }}
              />
              <span>+</span> {t("lessonPlan.home.addFiles")}
            </label>
            <span className="lesson-composer-hint">
              {prompt.trim() ? t(prompt.trim().length === 1 ? "lessonPlan.home.charCount.one" : "lessonPlan.home.charCount.other", { count: prompt.trim().length }) : t("lessonPlan.home.dropHint")}
            </span>
            <button className="lesson-button primary" type="button" onClick={submit} disabled={creating || (!prompt.trim() && !files.length)}>
              {creating ? t("lessonPlan.home.creating") : t("lessonPlan.home.create")}
            </button>
          </div>

          <div className="lesson-quick-starts">
            <span>{t("lessonPlan.home.quickStartLabel")}</span>
            {QUICK_STARTS.map((item) => (
              <button type="button" key={item.label} onClick={() => fillQuickStart(item.prompt)}>{t(item.label)}</button>
            ))}
          </div>
        </section>

        <section className="lesson-projects" aria-busy={loading}>
          <div className="lesson-section-head">
            <div>
              <span className="lesson-eyebrow">RECENT PROJECTS</span>
              <h2>{t("lessonPlan.home.recentProjects")}</h2>
            </div>
            <span>{t(projects.length === 1 ? "lessonPlan.home.projectCount.one" : "lessonPlan.home.projectCount.other", { count: projects.length })}</span>
          </div>

          {error ? (
            <div className="lesson-empty-projects">
              <strong>{t("lessonPlan.home.loadFailed")}</strong>
              <button type="button" className="lesson-button secondary" onClick={onRetry}>{t("lessonPlan.home.retry")}</button>
            </div>
          ) : loading ? (
            <div className="lesson-empty-projects"><span className="lesson-spinner" aria-hidden="true" /><strong>{t("lessonPlan.home.loading")}</strong></div>
          ) : projects.length ? (
            <div className="lesson-project-list">
              {projects.map((project) => (
                <article className="lesson-project-card" key={project.id}>
                  <button type="button" className="lesson-project-open" onClick={() => onOpen(project)}>
                    <div className="lesson-project-meta">
                      <span>{t("lessonPlan.home.projectType")}</span>
                      <i aria-hidden="true" />
                      <span>{t(project.page_count === 1 ? "lessonPlan.home.pageCount.one" : "lessonPlan.home.pageCount.other", { count: project.page_count })}</span>
                      <b>{t("lessonPlan.home.openProject")}</b>
                    </div>
                    <h3>{project.title}</h3>
                    <p>{project.brief_summary || project.request_text || t("lessonPlan.home.emptyBrief")}</p>
                    <small>{formatDate(new Date(project.updated_at), { dateStyle: "medium", timeStyle: "short" })}</small>
                  </button>
                  <button
                    type="button"
                    className="lesson-project-delete"
                    onClick={() => onDelete(project)}
                    aria-label={t("lessonPlan.home.deleteProject", { title: project.title })}
                    title={t("lessonPlan.home.deleteProject", { title: project.title })}
                  >
                    <span aria-hidden="true">×</span>
                  </button>
                </article>
              ))}
            </div>
          ) : (
            <div className="lesson-empty-projects">
              <span aria-hidden="true">✦</span>
              <strong>{t("lessonPlan.home.emptyTitle")}</strong>
              <p>{t("lessonPlan.home.emptyHint")}</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
