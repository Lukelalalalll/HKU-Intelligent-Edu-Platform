/**
 * Studio landing page: describe a class, start a deck and reopen recent work.
 */
import React, { useEffect, useRef, useState } from "react";
import type { PptProject } from "../../api";
import { useI18n, type TranslationKey } from "../../i18n";
import AuthedImage from "../../shared/components/AuthedImage";
import { StudioIcon } from "./icons";
import { stageKey } from "./stages";

export type StudioHomeProps = {
  projects: PptProject[];
  loading: boolean;
  error: string | null;
  creating: boolean;
  removingIds: Record<string, boolean>;
  onCreate: (text: string, files: File[]) => void;
  onOpen: (project: PptProject) => void;
  onDelete: (project: PptProject) => void;
  onRetry: () => void;
};

/** Landing surface for the courseware studio. */
export default function StudioHome({ projects, loading, error, creating, removingIds, onCreate, onOpen, onDelete, onRetry }: StudioHomeProps) {
  const { t, formatDate } = useI18n();
  const [text, setText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const menuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!openMenu) return;
    const close = (event: MouseEvent) => {
      if (menuRef.current?.contains(event.target as Node)) return;
      setOpenMenu(null);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [openMenu]);

  useEffect(() => {
    const node = inputRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(220, Math.max(96, node.scrollHeight))}px`;
  }, [text]);

  const submit = () => {
    if (!text.trim() || creating) return;
    onCreate(text, files);
    setText("");
    setFiles([]);
  };

  const addFiles = (incoming: FileList | File[] | null) => {
    if (!incoming) return;
    setFiles((current) => [...current, ...Array.from(incoming)]);
  };

  const stageLabel = (project: PptProject) => t(stageKey(project.current_stage));

  const quickStarts: { label: TranslationKey; prompt: TranslationKey }[] = [
    { label: "coursewareAgent.home.quickStarts.lecture", prompt: "coursewareAgent.home.quickStartPrompts.lecture" },
    { label: "coursewareAgent.home.quickStarts.seminar", prompt: "coursewareAgent.home.quickStartPrompts.seminar" },
    { label: "coursewareAgent.home.quickStarts.review", prompt: "coursewareAgent.home.quickStartPrompts.review" },
    { label: "coursewareAgent.home.quickStarts.flipped", prompt: "coursewareAgent.home.quickStartPrompts.flipped" },
  ];

  const fillQuickStart = (prompt: TranslationKey) => {
    setText(t(prompt));
    requestAnimationFrame(() => inputRef.current?.focus());
  };

  return (
    <div className="st-home" data-testid="studio-home">
      <div className="st-home-inner">
        <header className="st-home-head">
          <span className="st-eyebrow"><StudioIcon name="sparkle" size={13} /> {t("coursewareAgent.home.eyebrow")}</span>
          <h1>{t("coursewareAgent.home.titleLead")}<br /><span>{t("coursewareAgent.home.titleAccent")}</span></h1>
          <p>{t("coursewareAgent.home.subtitle")}</p>
        </header>

        <section className={`st-composer ${dragging ? "is-dragging" : ""}`} aria-label={t("coursewareAgent.home.composerLabel")}
          onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files); }}>
          <label className="st-composer-label" htmlFor="st-home-prompt">{t("coursewareAgent.home.composerLabel")}</label>
          <textarea
            id="st-home-prompt"
            ref={inputRef}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              const composing = event.nativeEvent.isComposing || event.keyCode === 229;
              if (event.key === "Enter" && !event.shiftKey && !composing) { event.preventDefault(); submit(); }
            }}
            placeholder={t("coursewareAgent.home.composerPlaceholder")}
            rows={4}
            disabled={creating}
          />
          {files.length ? (
            <div className="st-composer-files">
              {files.map((file) => (
                <span key={`${file.name}-${file.lastModified}`}>
                  <StudioIcon name="file" size={13} /> <b>{file.name}</b>
                  <button type="button" aria-label={t("common.actions.delete")} onClick={() => setFiles((current) => current.filter((item) => item !== file))}><StudioIcon name="close" size={12} /></button>
                </span>
              ))}
            </div>
          ) : null}
          <div className="st-composer-foot">
            <div className="st-composer-tools">
              <label className="st-ghost-button st-attach-button">
                <StudioIcon name="attach" size={15} /> {t("coursewareAgent.home.addMaterials")}
                <input type="file" multiple accept=".pdf,.pptx,.docx,.xlsx,.xls,.txt,.md,.markdown,.csv,.json,image/png,image/jpeg,image/webp" onChange={(event) => { addFiles(event.target.files); event.currentTarget.value = ""; }} />
              </label>
              <small>{files.length ? t("coursewareAgent.home.attachmentsHint") : t("coursewareAgent.home.hint")}</small>
            </div>
            <button type="button" className="st-primary-button" onClick={submit} disabled={creating || !text.trim()}>
              {creating ? t("coursewareAgent.home.creating") : t("coursewareAgent.home.create")}
              <StudioIcon name="next" size={15} />
            </button>
          </div>
        </section>

        <div className="st-quickstarts">
          <span className="st-quickstarts-label">{t("coursewareAgent.home.quickStartLabel")}</span>
          {quickStarts.map((item) => (
            <button key={item.label} type="button" className="st-chip" onClick={() => fillQuickStart(item.prompt)}>{t(item.label)}</button>
          ))}
        </div>
        <p className="st-flow-hint">{t("coursewareAgent.home.flowHint")}</p>

        <section className="st-recent">
          <header className="st-recent-head">
            <h2>{t("coursewareAgent.home.recentTitle")}</h2>
            <span>{t(projects.length === 1 ? "coursewareAgent.home.projectCount.one" : "coursewareAgent.home.projectCount.other", { count: projects.length })}</span>
          </header>

          {loading ? (
            <div className="st-deck-grid" aria-hidden="true">
              {[0, 1, 2].map((item) => (
                <div key={item} className="st-deck-card is-skeleton">
                  <div className="st-deck-cover" />
                  <span className="st-skeleton-line" />
                  <span className="st-skeleton-line is-short" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="st-recent-error" role="alert">
              <p>{error}</p>
              <button type="button" className="st-ghost-button" onClick={onRetry}><StudioIcon name="refresh" size={14} /> {t("coursewareAgent.home.retry")}</button>
            </div>
          ) : projects.length ? (
            <div className="st-deck-grid">
              {projects.map((project) => (
                <article key={project.id} className={`st-deck-card ${removingIds[project.id] ? "is-removing" : ""}`}>
                  <button type="button" className="st-deck-main" onClick={() => onOpen(project)}>
                    <div className="st-deck-cover">
                      {project.cover_preview_url ? (
                        <AuthedImage
                          src={project.cover_preview_url}
                          alt={t("coursewareAgent.home.coverAlt", { title: project.title })}
                          placeholder={<span className="st-deck-cover-fallback">{project.page_count ? <b>{project.page_count}</b> : null}<StudioIcon name="sparkle" size={18} /></span>}
                        />
                      ) : (
                        <span className="st-deck-cover-fallback">{project.page_count ? <b>{project.page_count}</b> : null}<StudioIcon name="sparkle" size={18} /></span>
                      )}
                    </div>
                    <strong className="st-deck-title">{project.title}</strong>
                    <span className="st-deck-meta">
                      {stageLabel(project)}
                      <i aria-hidden="true" />
                      {t(project.page_count === 1 ? "coursewareAgent.home.pagesCount.one" : "coursewareAgent.home.pagesCount.other", { count: project.page_count || 0 })}
                      <i aria-hidden="true" />
                      {t("coursewareAgent.home.updatedOn", { date: formatDate(project.updated_at, { month: "short", day: "numeric" }) })}
                    </span>
                  </button>
                  <div className="st-deck-menu" ref={openMenu === project.id ? menuRef : undefined}>
                    <button type="button" className="st-icon-button" aria-label={t("coursewareAgent.home.openMenu", { title: project.title })} aria-haspopup="menu" aria-expanded={openMenu === project.id} onClick={() => setOpenMenu((current) => current === project.id ? null : project.id)}>
                      <StudioIcon name="more" size={16} />
                    </button>
                    {openMenu === project.id ? (
                      <div className="st-menu" role="menu">
                        <button type="button" role="menuitem" onClick={() => { setOpenMenu(null); onDelete(project); }}>
                          <StudioIcon name="trash" size={14} /> {t("coursewareAgent.home.deleteProject")}
                        </button>
                      </div>
                    ) : null}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="st-recent-empty">
              <span className="st-recent-empty-mark" aria-hidden="true"><StudioIcon name="pages" size={20} /></span>
              <strong>{t("coursewareAgent.home.emptyTitle")}</strong>
              <p>{t("coursewareAgent.home.emptyBody")}</p>
            </div>
          )}
        </section>
      </div>

      <div className="st-home-glow" aria-hidden="true" />
    </div>
  );
}
