/**
 * Storyboard surface: review and edit the page outline before visuals.
 */
import React, { useRef, useState } from "react";
import toast from "react-hot-toast";
import type { PptPage } from "../../api";
import { useI18n } from "../../i18n";
import { HKUDialog } from "../../shared/components/HKUDialog";
import ChatPanel from "./ChatPanel";
import { StudioIcon } from "./icons";
import type { StudioModel } from "./types";

export type OutlineSurfaceProps = { model: StudioModel };

/** Outline review and editing. */
export default function OutlineSurface({ model }: OutlineSurfaceProps) {
  const { t } = useI18n();
  const { project, pages, messages, outlineGenerating, actions } = model;
  const ordered = [...pages].sort((a, b) => a.sort_order - b.sort_order);
  const page = ordered[model.selected] || ordered[0];
  const sections = new Set(ordered.map((item) => item.section_title).filter(Boolean));
  const [dragId, setDragId] = useState<string | null>(null);
  const [editingPage, setEditingPage] = useState<PptPage | null>(null);
  const [draft, setDraft] = useState({ section_title: "", title: "", bullets: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suppressClickRef = useRef(false);

  const openEditor = (target: PptPage) => {
    if (suppressClickRef.current) return;
    setEditingPage(target);
    setDraft({ section_title: target.section_title || "", title: target.title || "", bullets: (target.bullets || []).join("\n") });
    setError(null);
  };
  const closeEditor = () => { if (!saving) { setEditingPage(null); setError(null); } };
  const saveEditor = async () => {
    if (!editingPage) return;
    const title = draft.title.trim();
    if (!title) { setError(t("coursewareAgent.outline.titleRequired")); return; }
    const bullets = draft.bullets.split(/\r?\n/).map((item) => item.trim()).filter(Boolean).slice(0, 8);
    setSaving(true); setError(null);
    try {
      await actions.patchPage(editingPage, { title, bullets, section_title: draft.section_title.trim() });
      setEditingPage(null);
      toast.success(t("coursewareAgent.outline.saved"));
    } catch (requestError: any) {
      setError(requestError?.response?.data?.detail || requestError?.message || t("coursewareAgent.outline.saveFailed"));
    } finally {
      setSaving(false);
    }
  };

  const move = (id: string, delta: number) => {
    const ids = ordered.map((item) => item.id);
    const from = ids.indexOf(id);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= ids.length) return;
    ids.splice(from, 1);
    ids.splice(to, 0, id);
    actions.reorderPages(ids);
  };

  const onDrop = (target: PptPage) => {
    if (!dragId || dragId === target.id) return;
    const ids = ordered.map((item) => item.id);
    const from = ids.indexOf(dragId);
    const to = ids.indexOf(target.id);
    if (from < 0 || to < 0) return;
    ids.splice(from, 1);
    ids.splice(to, 0, dragId);
    actions.reorderPages(ids);
  };

  return (
    <div className="st-surface st-outline" data-testid="studio-surface-outline">
      <header className="st-surface-head">
        <div>
          <span className="st-eyebrow">02 · {t("coursewareAgent.workspace.steps.storyboard")}</span>
          <h2>{t("coursewareAgent.outline.title")}</h2>
          <p>{t("coursewareAgent.outline.subtitle")}</p>
        </div>
        <span className="st-state-pill">
          {t(ordered.length === 1 ? "coursewareAgent.outline.pageCount.one" : "coursewareAgent.outline.pageCount.other", { count: ordered.length })}
          <i aria-hidden="true" />
          {t(sections.size === 1 ? "coursewareAgent.outline.sectionCount.one" : "coursewareAgent.outline.sectionCount.other", { count: sections.size })}
        </span>
      </header>

      <div className="st-surface-body st-outline-body">
        <section className="st-card st-outline-board">
          {outlineGenerating ? (
            <div className="st-generating">
              <span className="st-generating-mark" aria-hidden="true"><StudioIcon name="sparkle" size={22} /></span>
              <h3>{t("coursewareAgent.requirements.generating")}</h3>
              <div className="st-generating-bar" role="status"><i /></div>
            </div>
          ) : (
            <div className="st-outline-grid">
              {ordered.map((item, index) => (
                <article
                  key={item.id}
                  draggable
                  className={`st-outline-card ${dragId === item.id ? "is-dragging" : ""}`}
                  onDragStart={() => { suppressClickRef.current = true; setDragId(item.id); }}
                  onDragEnd={() => { window.setTimeout(() => { suppressClickRef.current = false; }, 80); setDragId(null); }}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={() => onDrop(item)}
                  onClick={() => openEditor(item)}
                >
                  <div className="st-outline-card-top">
                    <span className="st-outline-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className="st-outline-section">{item.section_title || t("coursewareAgent.outline.untitledSection")}</span>
                    <div className="st-outline-actions" onClick={(event) => event.stopPropagation()}>
                      <button type="button" disabled={index === 0} onClick={() => move(item.id, -1)} title={t("coursewareAgent.outline.moveUp")} aria-label={t("coursewareAgent.outline.moveUp")}>
                        <StudioIcon name="back" size={13} />
                      </button>
                      <button type="button" disabled={index === ordered.length - 1} onClick={() => move(item.id, 1)} title={t("coursewareAgent.outline.moveDown")} aria-label={t("coursewareAgent.outline.moveDown")}>
                        <StudioIcon name="next" size={13} />
                      </button>
                      <button type="button" onClick={() => openEditor(item)} title={t("coursewareAgent.outline.editAction")} aria-label={t("coursewareAgent.outline.editAction")}>
                        <StudioIcon name="edit" size={13} />
                      </button>
                    </div>
                  </div>
                  <h3>{item.title}</h3>
                  <ul>
                    {(item.bullets || []).slice(0, 4).map((bullet) => <li key={bullet}>{bullet}</li>)}
                    {!(item.bullets || []).length ? <li className="is-empty">{t("coursewareAgent.visual.noBullets")}</li> : null}
                  </ul>
                  <small>{t("coursewareAgent.outline.cardHint")}</small>
                </article>
              ))}
            </div>
          )}
        </section>

        <aside className="st-card st-outline-chat">
          <header className="st-card-head">
            <div>
              <strong>{t("coursewareAgent.outline.agentTitle")}</strong>
              <small>{t("coursewareAgent.outline.agentSubtitle", { page: page ? page.sort_order + 1 : 1 })}</small>
            </div>
            <span className="st-mark" aria-hidden="true"><StudioIcon name="sparkle" size={14} /></span>
          </header>
          <ChatPanel
            project={project}
            page={page}
            messages={messages.filter((message) => !message.page_id || message.page_id === page?.id)}
            requirement={model.requirement}
            onSent={actions.refresh}
            onBeforeAgent={actions.flushAutosave}
            onAgentSlideFocus={actions.selectPage}
          />
        </aside>
      </div>

      <footer className="st-surface-foot">
        <span className="st-foot-hint">
          {t(ordered.length === 1 ? "coursewareAgent.outline.pageCount.one" : "coursewareAgent.outline.pageCount.other", { count: ordered.length })}
          <i aria-hidden="true" />
          {t(sections.size === 1 ? "coursewareAgent.outline.sectionCount.one" : "coursewareAgent.outline.sectionCount.other", { count: sections.size })}
        </span>
        <div className="st-foot-actions">
          <button type="button" className="st-ghost-button" onClick={() => actions.navigate("start")}>
            <StudioIcon name="back" size={14} /> {t("coursewareAgent.workspace.back")}
          </button>
          <button type="button" className="st-primary-button" onClick={actions.confirmOutline} disabled={!ordered.length || outlineGenerating}>
            {outlineGenerating ? t("coursewareAgent.outline.confirming") : t("coursewareAgent.outline.confirm")}
            <StudioIcon name="next" size={15} />
          </button>
        </div>
      </footer>

      <HKUDialog
        open={Boolean(editingPage)}
        onClose={closeEditor}
        scope="viewport"
        title={editingPage ? t("coursewareAgent.outline.editTitlePage", { page: editingPage.sort_order + 1 }) : t("coursewareAgent.outline.editTitle")}
        description={t("coursewareAgent.outline.editDescription")}
        className="st-outline-dialog"
      >
        <div className="st-form">
          <label>
            {t("coursewareAgent.outline.sectionTitleLabel")}
            <input value={draft.section_title} onChange={(event) => setDraft((current) => ({ ...current, section_title: event.target.value }))} placeholder={t("coursewareAgent.outline.sectionTitlePlaceholder")} />
          </label>
          <label>
            {t("coursewareAgent.outline.pageTitleLabel")}
            <input value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} placeholder={t("coursewareAgent.outline.pageTitlePlaceholder")} autoFocus />
          </label>
          <label>
            {t("coursewareAgent.outline.bulletsLabel")}
            <textarea value={draft.bullets} onChange={(event) => setDraft((current) => ({ ...current, bullets: event.target.value }))} rows={8} placeholder={t("coursewareAgent.outline.bulletsPlaceholder")} />
          </label>
          {error ? <p className="st-form-error" role="alert">{error}</p> : null}
          <div className="st-form-actions">
            <button type="button" className="st-ghost-button" onClick={closeEditor} disabled={saving}>{t("common.actions.cancel")}</button>
            <button type="button" className="st-primary-button" onClick={() => void saveEditor()} disabled={saving || !draft.title.trim()}>
              {saving ? t("coursewareAgent.outline.saving") : t("common.actions.save")}
            </button>
          </div>
        </div>
      </HKUDialog>
    </div>
  );
}
