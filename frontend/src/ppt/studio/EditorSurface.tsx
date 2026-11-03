/**
 * Editor surface: page thumbnails, canvas and the page Agent drawer.
 */
import React, { useEffect, useRef, useState } from "react";
import { pptApi, type PptDocument } from "../../api";
import { useI18n } from "../../i18n";
import { editableDocument, SlideThumbnail } from "../SlideRenderer";
import SceneGraphEditor from "../SceneGraphEditor";
import ChatPanel from "./ChatPanel";
import { StudioIcon } from "./icons";
import type { StudioModel } from "./types";

export type EditorSurfaceProps = { model: StudioModel };

/** Page-by-page editing with an Agent drawer. */
export default function EditorSurface({ model }: EditorSurfaceProps) {
  const { t } = useI18n();
  const { project, pages, selected, messages, autosaveSaving, actions } = model;
  const page = pages[selected] || pages[0];
  const [agentOpen, setAgentOpen] = useState(false);
  const thumbsRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const list = thumbsRef.current;
    if (!list) return;
    const active = list.querySelector(".ppt-thumbnail-card.active") || list.children[selected];
    if (active instanceof HTMLElement) active.scrollIntoView({ block: "nearest" });
  }, [selected]);

  useEffect(() => {
    if (!agentOpen) return;
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") setAgentOpen(false); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [agentOpen]);

  if (!page) {
    return (
      <div className="st-surface st-editor" data-testid="studio-surface-editor">
        <div className="st-empty-block">
          <span aria-hidden="true"><StudioIcon name="layout" size={22} /></span>
          <p>{t("coursewareAgent.project.loading")}</p>
        </div>
      </div>
    );
  }

  const saveDocument = (document: PptDocument) => actions.scheduleSave(page, document);

  return (
    <div className="st-surface st-editor" data-testid="studio-surface-editor">
      <div className="st-editor-layout">
        <aside className="st-thumbs">
          <header className="st-card-mini-head">
            <strong>{t("coursewareAgent.editor.pagesTitle")}</strong>
            <span>{pages.length}</span>
          </header>
          <div className="st-thumb-list" ref={thumbsRef}>
            {pages.map((item, index) => (
              <div key={item.id} className="st-thumb-item">
                <SlideThumbnail page={{ ...item, sort_order: index }} selected={index === selected} onClick={() => actions.selectPage(index)} />
              </div>
            ))}
          </div>
        </aside>

        <main className="st-editor-main">
          <header className="st-editor-head">
            <div>
              <span className="st-eyebrow">{t("coursewareAgent.workspace.steps.edit")} · {t("coursewareAgent.editor.pageOf", { current: selected + 1, total: pages.length })}</span>
              <strong title={page.title}>{page.title}</strong>
            </div>
            <div className="st-editor-head-actions">
              <div className="st-editor-pager">
                <button type="button" className="st-icon-button" disabled={selected === 0} onClick={() => actions.selectPage(selected - 1)} aria-label={t("coursewareAgent.present.previous")}><StudioIcon name="back" size={15} /></button>
                <span>{t("coursewareAgent.editor.pageOf", { current: selected + 1, total: pages.length })}</span>
                <button type="button" className="st-icon-button" disabled={selected === pages.length - 1} onClick={() => actions.selectPage(selected + 1)} aria-label={t("coursewareAgent.present.next")}><StudioIcon name="next" size={15} /></button>
              </div>
              <span className={`st-save-state ${autosaveSaving ? "is-saving" : ""}`}><i aria-hidden="true" /> {autosaveSaving ? t("coursewareAgent.workspace.saving") : t("coursewareAgent.workspace.saved")}</span>
              <button type="button" className={`st-ghost-button ${agentOpen ? "is-active" : ""}`} onClick={() => setAgentOpen((current) => !current)} aria-expanded={agentOpen} aria-label={t("coursewareAgent.editor.askAgent")}>
                <StudioIcon name="sparkle" size={14} /> <span>{t("coursewareAgent.editor.askAgent")}</span>
              </button>
            </div>
          </header>

          <div className="st-canvas-wrap">
            <SceneGraphEditor
              document={editableDocument(page)}
              editable
              onChange={saveDocument}
              onUploadImage={async (file) => {
                const { data } = await pptApi.editorAsset(page.project_id, file, page.id);
                return data;
              }}
            />
          </div>
        </main>

        <aside className={`st-agent-drawer ${agentOpen ? "is-open" : ""}`} data-testid="ppt-agent-dialog" aria-hidden={!agentOpen} aria-label={t("coursewareAgent.editor.agentTitle")}>
          <header className="st-agent-drawer-head">
            <div>
              <span className="st-eyebrow">{t("coursewareAgent.editor.askAgent")}</span>
              <strong>{t("coursewareAgent.editor.agentTitle")}</strong>
              <small>{t("coursewareAgent.editor.agentSubtitle", { page: page.sort_order + 1 })}</small>
            </div>
            <button type="button" className="st-icon-button" onClick={() => setAgentOpen(false)} title={t("coursewareAgent.editor.closeAgent")} aria-label={t("coursewareAgent.editor.closeAgent")}>
              <StudioIcon name="close" size={16} />
            </button>
          </header>
          <ChatPanel
            project={project}
            page={page}
            messages={messages.filter((message) => message.page_id === page.id)}
            requirement={null}
            onSent={actions.refresh}
            onBeforeAgent={actions.flushAutosave}
            onAgentSlideFocus={actions.selectPage}
            className="st-agent-drawer-chat"
          />
        </aside>
      </div>
    </div>
  );
}
