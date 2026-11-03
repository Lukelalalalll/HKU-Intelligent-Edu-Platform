/**
 * PPT studio workspace: requirement chat, outline, visual research, theme,
 * layouting, preview editing and presentation.
 */
import React, { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";
import { PptChatStreamEvent, PptDocument, PptMessage, PptPage, PptPagePatch, PptProject, PptSlideElement, PptRequirement, PptSource, PptTheme, pptApi } from "../api";
import { SLIDE_HEIGHT, SLIDE_WIDTH, SlideRenderer, SlideThumbnail, editableDocument } from "./SlideRenderer";
import SceneGraphEditor from "./SceneGraphEditor";
import { HKUConfirmDialog, HKUDialog } from "../shared/components/HKUDialog";
import WelcomeBanner from "../shared/components/WelcomeBanner";
import { getApiErrorMessage } from "../lib/apiClient";
import { usePptAutosave } from "../hooks/usePptAutosave";
import { usePptGeneration } from "../hooks/usePptGeneration";
import { useI18n, type TranslationKey, type Translator } from "../i18n";

type Surface = "start" | "outline" | "visual" | "theme" | "layouting" | "editor" | "present";
const stageKeys: Record<string, TranslationKey> = { init: "coursewareAgent.stages.init", outline: "coursewareAgent.stages.outline", visual: "coursewareAgent.stages.visual", theme: "coursewareAgent.stages.theme", layout: "coursewareAgent.stages.layout", design: "coursewareAgent.stages.design", export: "coursewareAgent.stages.export" };
/** Translate a backend stage code, falling back to the generic in-progress label. */
function stageLabel(stage: string, t: Translator): string { const key = stageKeys[stage]; return key ? t(key) : t("coursewareAgent.stages.inProgress"); }
const deepseekModels = ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-v4-flash-vision-exp"];

function StudioRail({ surface, onNavigate }: { surface: Surface; onNavigate: (surface: Surface) => void }) {
  const { t } = useI18n();
  return <aside className="ppt-studio-rail" aria-label={t("coursewareAgent.rail.navigation")}>
    <div className="ppt-rail-mark">✦</div>
    <button className={surface === "start" ? "active" : ""} onClick={() => onNavigate("start")} title={t("coursewareAgent.rail.chat")}><span>◌</span><small>{t("coursewareAgent.rail.chat")}</small></button>
    <button className={surface === "outline" ? "active" : ""} onClick={() => onNavigate("outline")} title={t("coursewareAgent.rail.storyboard")}><span>▤</span><small>{t("coursewareAgent.rail.storyboard")}</small></button>
    <button className={surface === "editor" ? "active" : ""} onClick={() => onNavigate("editor")} title={t("coursewareAgent.rail.editor")}><span>◫</span><small>{t("coursewareAgent.rail.edit")}</small></button>
    <button className={surface === "present" ? "active" : ""} onClick={() => onNavigate("present")} title={t("coursewareAgent.rail.present")}><span>▷</span><small>{t("coursewareAgent.rail.present")}</small></button>
    <div className="ppt-rail-spacer" />
    <button title={t("coursewareAgent.rail.help")}><span>?</span><small>{t("coursewareAgent.rail.help")}</small></button>
  </aside>;
}

function StudioHomeHeader() {
  const { t } = useI18n();
  return <header className="ppt-studio-home-header"><div className="ppt-studio-home-logo"><b>HKU</b><span>INTELLIGENT EDU</span></div><div className="ppt-studio-home-context">{t("coursewareAgent.homeHeader.workspace")} <i /> {t("coursewareAgent.homeHeader.tagline")}</div><div className="ppt-studio-home-actions"><button title={t("coursewareAgent.homeHeader.shortcuts")}>⌘ /</button><button title={t("coursewareAgent.homeHeader.notifications")}>◔</button><div className="ppt-studio-avatar">T</div></div></header>;
}

function SlideCanvas({ page, editable, onChange }: { page: PptPage; editable: boolean; onChange?: (doc: PptDocument) => void }) {
  const document = editableDocument(page);
  return <SceneGraphEditor document={document} editable={editable} onChange={onChange} onUploadImage={async (file) => {
    const projectId = page.project_id;
    const { data } = await pptApi.editorAsset(projectId, file, page.id);
    return data;
  }} />;
}

function Chat({ project, page, messages, requirement, sources, onSent, onUpload, onBeforeAgent, onAgentSlideFocus, onRequirementUpdate }: { project: PptProject; page?: PptPage; messages: PptMessage[]; requirement?: PptRequirement | null; sources?: PptSource[]; onSent: () => void | Promise<void>; onUpload?: (files: FileList) => void; onBeforeAgent?: () => Promise<void>; onAgentSlideFocus?: (index: number) => void; onRequirementUpdate?: (response: any) => void }) {
  const { t } = useI18n();
  const [value, setValue] = useState(""); const [sending, setSending] = useState(false); const [streamText, setStreamText] = useState(""); const [activities, setActivities] = useState<PptChatStreamEvent[]>([]); const [optimistic, setOptimistic] = useState<PptMessage | null>(null); const abortRef = useRef<AbortController | null>(null); const streamRef = useRef<HTMLDivElement | null>(null);
  const lastAssistant = [...messages].reverse().find((item) => item.role === "assistant");
  const question = !page ? (lastAssistant?.payload?.question || requirement?.questions?.[0]) : null;
  useEffect(() => () => abortRef.current?.abort(), []);
  const send = async (content = value.trim(), option?: string) => {
    if ((!content && !option) || sending) return;
    const text = content || option || "";
    setSending(true); setValue(""); setStreamText(""); setActivities([]); setOptimistic({ id: `optimistic-${Date.now()}`, role: "user", stage: page ? "editor" : "init", scope_type: page ? "page" : "project", page_id: page?.id, content_md: text, payload: {}, created_at: new Date().toISOString() });
    if (!page) { const controller = new AbortController(); abortRef.current = controller; try { const complete = await pptApi.streamRequirementChat(project.id, { content: text, option_id: option, option_label: option }, { onEvent: (event) => { if (event.type === "chunk") setStreamText((current) => current + (event.chunk || "")); if (event.type === "complete" && event.requirement) onRequirementUpdate?.(event.requirement); } }, controller.signal); if (complete?.requirement) onRequirementUpdate?.(complete.requirement); await onSent(); } catch (e: any) { if (e?.name !== "AbortError") toast.error(e.response?.data?.detail || e.message || t("coursewareAgent.chat.sendFailed")); } finally { abortRef.current = null; setSending(false); setOptimistic(null); setStreamText(""); } return; }
    const controller = new AbortController(); abortRef.current = controller;
    try {
      await onBeforeAgent?.();
      await pptApi.streamMessage(project.id, { content: text, page_id: page.id, ui_surface: "editor" }, { onEvent: (event) => { if (event.type === "chunk") setStreamText((current) => current + (event.chunk || "")); if (event.type === "trace") { setActivities((current) => [...current, event]); const target = event.trace?.slideIndex; if (typeof target === "number" && target >= 0) onAgentSlideFocus?.(target); } } }, controller.signal);
      await onSent();
    } catch (e: any) { if (e?.name !== "AbortError") toast.error(e.response?.data?.detail || e.message || t("coursewareAgent.chat.sendFailed")); } finally { abortRef.current = null; setSending(false); setActivities([]); setStreamText(""); }
  };
  const stop = () => { abortRef.current?.abort(); abortRef.current = null; setSending(false); };
  useEffect(() => { const node = streamRef.current; if (node) node.scrollTop = node.scrollHeight; }, [messages, streamText, optimistic]);
 return <section className="ppt-conversation"><div className="ppt-conversation-head"><div><span className="ppt-kicker">{t("coursewareAgent.chat.kicker")}</span><strong>{page ? t("coursewareAgent.chat.discussingPage", { page: page.sort_order + 1 }) : t("coursewareAgent.chat.lead")}</strong></div><span className="ppt-online"><i /> {t("coursewareAgent.status.online")}</span></div><div className="ppt-conversation-stream" ref={streamRef}>{messages.length || optimistic ? <>{messages.map((message) => <div key={message.id} className={`ppt-message ppt-message-enter ${message.role === "user" ? "user" : "assistant"}`}><div>{message.content_md}</div>{message.payload?.action_type && <small>{t("coursewareAgent.chat.executed", { action: message.payload.action_type })}</small>}</div>)}{optimistic && <div className="ppt-message user ppt-message-enter ppt-message-pending"><div>{optimistic.content_md}</div><small>{t("coursewareAgent.chat.sending")}</small></div>}</> : <div className="ppt-chat-empty"><div className="ppt-chat-orb">✦</div><h3>{t("coursewareAgent.chat.emptyTitle")}</h3><p>{t("coursewareAgent.chat.emptyBody")}</p></div>}{sending && <div className="ppt-message assistant ppt-agent-live ppt-message-enter"><div>{streamText || t("coursewareAgent.chat.understanding")}<span className="ppt-typing-caret" /></div>{activities.map((event, index) => <small key={`${event.trace?.tool}-${index}`}>{event.trace?.status === "success" ? "✓" : event.trace?.status === "error" ? "!" : "⋯"} {event.trace?.message || event.status}</small>)}</div>}{!page && question?.options?.length ? <div className="ppt-requirement-options">{question.options.map((option: string) => <button key={option} onClick={() => void send("", option)} disabled={sending}>{option}</button>)}</div> : null}{!page && sources?.length ? <div className="ppt-attachment-list">{sources.map((source) => <span key={source.id}>📎 {source.title}</span>)}</div> : null}</div><div className="ppt-composer"><textarea value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }} placeholder={page ? t("coursewareAgent.chat.placeholderPage") : t("coursewareAgent.chat.placeholderProject")} rows={3} disabled={sending} /><div className="ppt-composer-tools">{onUpload && <label className="ppt-upload-button">{t("coursewareAgent.chat.addMaterials")}<input type="file" multiple accept=".pdf,.pptx,.docx,.xlsx,.xls,.txt,.md,.markdown,.csv,.json,image/png,image/jpeg,image/webp" onChange={(e) => { if (e.target.files?.length) onUpload(e.target.files); e.currentTarget.value = ""; }} /></label>}{sending ? <button onClick={stop} aria-label={t("coursewareAgent.chat.stop")}>■</button> : <button onClick={() => void send()} disabled={!value.trim()} aria-label={t("coursewareAgent.chat.send")}>↑</button>}</div><small>{t("coursewareAgent.chat.composerHint")}</small></div></section>;
}

function OutlineBoard({ pages, onSelect, onReorder, onConfirm, onUpdate }: { pages: PptPage[]; onSelect: (page: PptPage) => void; onReorder: (ids: string[]) => void; onConfirm: () => void; onUpdate: (page: PptPage, payload: PptPagePatch) => Promise<PptPage> }) {
  const { t } = useI18n();
  const [dragId, setDragId] = useState<string | null>(null);
  const [editingPage, setEditingPage] = useState<PptPage | null>(null);
  const [draft, setDraft] = useState({ section_title: "", title: "", bullets: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const suppressClickRef = useRef(false);
  const ordered = [...pages].sort((a, b) => a.sort_order - b.sort_order);
  const openEditor = (page: PptPage) => {
    if (suppressClickRef.current) return;
    setEditingPage(page);
    setDraft({ section_title: page.section_title || "", title: page.title || "", bullets: (page.bullets || []).join("\n") });
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
      await onUpdate(editingPage, { title, bullets, section_title: draft.section_title.trim() });
      setEditingPage(null);
      toast.success(t("coursewareAgent.outline.saved"));
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || t("coursewareAgent.outline.saveFailed"));
    } finally { setSaving(false); }
  };
  return <section className="ppt-outline-board"><div className="ppt-board-head"><div><span className="ppt-kicker">OUTLINE BOARD</span><h2>{t("coursewareAgent.outline.title")}</h2><p>{t("coursewareAgent.outline.subtitle")}</p></div><button className="ppt-primary" onClick={onConfirm}>{t("coursewareAgent.outline.confirm")}</button></div><div className="ppt-board-grid">{ordered.map((page, index) => <article key={page.id} draggable onDragStart={() => { suppressClickRef.current = true; setDragId(page.id); }} onDragEnd={() => { window.setTimeout(() => { suppressClickRef.current = false; }, 100); setDragId(null); }} onDragOver={(e) => e.preventDefault()} onDrop={() => { if (!dragId || dragId === page.id) return; const ids = ordered.map((item) => item.id); const from = ids.indexOf(dragId); const to = ids.indexOf(page.id); ids.splice(from, 1); ids.splice(to, 0, dragId); onReorder(ids); }} onClick={() => { if (suppressClickRef.current) { suppressClickRef.current = false; return; } onSelect(page); openEditor(page); }} className="ppt-outline-card"><div className="ppt-outline-number">{String(index + 1).padStart(2, "0")}</div><span>{page.section_title || t("coursewareAgent.outline.untitledSection")}</span><h3>{page.title}</h3><ul>{page.bullets.slice(0, 4).map((bullet) => <li key={bullet}>{bullet}</li>)}</ul><small>{t("coursewareAgent.outline.cardHint")}</small></article>)}</div><HKUDialog open={Boolean(editingPage)} onClose={closeEditor} scope="viewport" eyebrow="EDIT OUTLINE" title={editingPage ? t("coursewareAgent.outline.editTitlePage", { page: editingPage.sort_order + 1 }) : t("coursewareAgent.outline.editTitle")} description={t("coursewareAgent.outline.editDescription")} className="ppt-outline-edit-dialog"><div className="ppt-outline-edit-form"><label>{t("coursewareAgent.outline.sectionTitleLabel")}<input value={draft.section_title} onChange={(event) => setDraft((current) => ({ ...current, section_title: event.target.value }))} placeholder={t("coursewareAgent.outline.sectionTitlePlaceholder")} /></label><label>{t("coursewareAgent.outline.pageTitleLabel")}<input value={draft.title} onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))} placeholder={t("coursewareAgent.outline.pageTitlePlaceholder")} autoFocus /></label><label>{t("coursewareAgent.outline.bulletsLabel")}<textarea value={draft.bullets} onChange={(event) => setDraft((current) => ({ ...current, bullets: event.target.value }))} rows={10} placeholder={t("coursewareAgent.outline.bulletsPlaceholder")} /></label>{error && <p className="ppt-outline-edit-error" role="alert">{error}</p>}<div className="hku-dialog-actions ppt-outline-edit-actions"><button type="button" className="ppt-ghost" onClick={closeEditor} disabled={saving}>{t("common.actions.cancel")}</button><button type="button" className="hku-dialog-confirm" onClick={() => void saveEditor()} disabled={saving || !draft.title.trim()}>{saving ? t("coursewareAgent.outline.saving") : t("common.actions.save")}</button></div></div></HKUDialog></section>;
}

function AgentFab({ open, onClick }: { open: boolean; onClick: () => void }) {
  const { t } = useI18n();
  return <button type="button" data-testid="ppt-agent-fab" className={`ppt-agent-fab ${open ? "is-open" : ""}`} onClick={onClick} aria-label={open ? t("coursewareAgent.agentFab.close") : t("coursewareAgent.agentFab.open")} aria-expanded={open} title={open ? t("coursewareAgent.agentFab.close") : t("coursewareAgent.agentFab.open")}>
    <i className="fas fa-robot" aria-hidden="true" />
    <span>Agent</span>
  </button>;
}

function AgentDialog({ open, onClose, pageNumber, children }: { open: boolean; onClose: () => void; pageNumber: number; children: React.ReactNode }) {
  const { t } = useI18n();
  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  return <aside data-testid="ppt-agent-dialog" className={`ppt-agent-dialog ${open ? "is-open" : ""}`} role="dialog" aria-modal="false" aria-labelledby="ppt-agent-dialog-title" aria-hidden={!open}>
    <header className="ppt-agent-dialog-head">
      <div><span className="ppt-kicker">PPT EDIT AGENT</span><strong id="ppt-agent-dialog-title">{t("coursewareAgent.agentDialog.title")}</strong><small>{t("coursewareAgent.agentDialog.discussingPage", { page: pageNumber })}</small></div>
      <span className="ppt-agent-dialog-status"><i /> {t("coursewareAgent.status.online")}</span>
      <button type="button" className="ppt-agent-dialog-close" onClick={onClose} aria-label={t("coursewareAgent.agentDialog.closeLabel")} title={t("common.dialog.close")}>×</button>
    </header>
    <div className="ppt-agent-dialog-body">{children}</div>
  </aside>;
}

function VisualStep({ pages, running, onRun, onContinue, onSave }: { pages: PptPage[]; running: boolean; onRun: () => void; onContinue: () => void; onSave: (page: PptPage, ids: string[]) => Promise<void> }) {
  const { t } = useI18n();
  const [index, setIndex] = useState(0); const [draft, setDraft] = useState<Record<string, string[]>>({}); const page = pages[index] || pages[0];
  const autoStarted = useRef(false);
  useEffect(() => { if (pages.length && !running && pages.every((p) => !(p.asset_manifest || []).length) && !autoStarted.current) { autoStarted.current = true; onRun(); } }, [pages.length, running, onRun]);
  const assets = (page?.asset_manifest || []).slice(0, 6); const selected = draft[page?.id || ""] ?? page?.selected_asset_ids ?? []; const pageVisualStatus = page?.visual_plan?.asset_status || page?.statuses?.visual || "empty"; const pageSearching = pageVisualStatus === "running" || (running && pageVisualStatus !== "ready" && pageVisualStatus !== "failed" && pageVisualStatus !== "degraded"); const ready = pages.filter((p) => p.statuses?.visual === "ready" || p.statuses?.visual === "failed" || p.statuses?.visual === "degraded" || (p.asset_manifest || []).length > 0).length; const progress = pages.length ? Math.round(ready / pages.length * 100) : 0;
  const toggle = (id: string) => setDraft((all) => { const current = all[page.id] ?? selected; return { ...all, [page.id]: current.includes(id) ? current.filter((x) => x !== id) : current.length < 6 ? [...current, id] : current }; });
  return <section className="ppt-visual-step"><div className="ppt-board-head"><div><span className="ppt-kicker">VISUAL RESEARCH</span><h2>{t("coursewareAgent.visual.title")}</h2><p>{t("coursewareAgent.visual.subtitle", { max: 6 })}</p></div><span className="ppt-theme-auto-hint">{t("coursewareAgent.visual.readyCount", { ready, total: pages.length })}</span></div><div className="ppt-visual-progress"><div className="ppt-visual-progress-head"><b>{running ? t("coursewareAgent.visual.progressRunning") : progress === 100 ? t("coursewareAgent.visual.progressReady") : t("coursewareAgent.visual.progressWaiting")}</b><span>{progress}%</span></div><div className="ppt-visual-progress-track"><i style={{ width: `${progress}%` }} /></div></div><div className="ppt-visual-review"><aside className="ppt-visual-outline"><div className="ppt-visual-review-title">{t("coursewareAgent.visual.outlineTitle")}</div>{pages.map((p, i) => <button key={p.id} className={i === index ? "active" : ""} onClick={() => setIndex(i)}><span>{t("coursewareAgent.visual.pageLabel", { page: i + 1 })} · {p.section_title || t("coursewareAgent.outline.untitledSection")}</span><b>{p.title}</b><small>{(p.bullets || []).slice(0, 2).join(" · ") || t("coursewareAgent.visual.noBullets")}</small></button>)}</aside><main className="ppt-visual-assets"><div className="ppt-visual-review-title"><span>{t("coursewareAgent.visual.pageLabel", { page: (page?.sort_order || index) + 1 })} · {page?.title}</span><small>{t("coursewareAgent.visual.selectedCount", { selected: selected.length, max: 6 })}</small></div><ul className="ppt-visual-bullets">{(page?.bullets || []).map((b) => <li key={b}>{b}</li>)}</ul><div className="ppt-visual-asset-grid">{assets.map((asset) => <button key={asset.id} className={`ppt-visual-asset ${selected.includes(asset.id) ? "selected" : ""}`} onClick={() => toggle(asset.id)}><div>{(asset.public_url || asset.src) ? <img src={asset.public_url || asset.src} alt={asset.alt || page.title} /> : <span>{t("coursewareAgent.visual.noPreview")}</span>}<i>{selected.includes(asset.id) ? "✓" : ""}</i></div><b>{asset.title || t("coursewareAgent.visual.untitledAsset")}</b><small>{asset.license || t("coursewareAgent.visual.licenseRecorded")} · {Math.round((asset.score || 0) * 100)}%</small></button>)}{!assets.length && <p className="ppt-visual-empty">{pageSearching ? t("coursewareAgent.visual.searching") : pageVisualStatus === "failed" ? (page?.visual_plan?.asset_error ? t("coursewareAgent.visual.searchFailedWithError", { error: page.visual_plan.asset_error }) : t("coursewareAgent.visual.searchFailedRetry")) : pageVisualStatus === "degraded" ? t("coursewareAgent.visual.degraded") : t("coursewareAgent.visual.noCandidates")}</p>}</div></main></div><div className="ppt-visual-step-actions"><button className="ppt-ghost" onClick={() => page && setDraft((all) => ({ ...all, [page.id]: assets.map((a) => a.id) }))}>{t("coursewareAgent.visual.selectAll")}</button><button className="ppt-ghost" onClick={() => page && setDraft((all) => ({ ...all, [page.id]: [] }))}>{t("coursewareAgent.visual.clearSelection")}</button><button className="ppt-primary" onClick={() => page && void onSave(page, selected)} disabled={!page}>{t("coursewareAgent.visual.confirmPage")}</button><button className="ppt-primary" onClick={onContinue} disabled={running || !pages.length}>{t("coursewareAgent.visual.continue")}</button><button className="ppt-ghost" onClick={onRun} disabled={running}>{running ? t("coursewareAgent.visual.retrieving") : t("coursewareAgent.visual.regenerate")}</button></div></section>;
}

function ThemeStep({ themes, selected, onSelect, disabled }: { themes: PptTheme[]; selected?: string | null; onSelect: (id: string) => void; disabled?: boolean }) {
  const { t } = useI18n();
  const [query, setQuery] = useState(""); const [family, setFamily] = useState("all");
  const families = Array.from(new Set(themes.map((t) => t.family))); const visible = themes.filter((t) => (family === "all" || t.family === family) && `${t.name} ${t.description}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="ppt-theme-step"><div className="ppt-board-head"><div><span className="ppt-kicker">CHOOSE THEME</span><h2>{t("coursewareAgent.theme.title")}</h2><p>{t("coursewareAgent.theme.subtitle")}</p></div><span className="ppt-theme-auto-hint">{t("coursewareAgent.theme.autoHint")}</span></div><div className="ppt-theme-toolbar"><input placeholder={t("coursewareAgent.theme.searchPlaceholder")} value={query} onChange={(e) => setQuery(e.target.value)} disabled={disabled} /><div>{["all", ...families].map((item) => <button key={item} className={family === item ? "active" : ""} onClick={() => setFamily(item)} disabled={disabled}>{item === "all" ? t("coursewareAgent.theme.allFamilies") : item}</button>)}</div></div><div className="ppt-theme-grid">{visible.map((theme) => <button key={theme.id} disabled={disabled} className={`ppt-theme-card ${selected === theme.id ? "selected" : ""}`} onClick={() => onSelect(theme.id)}><div className="ppt-theme-preview" style={{ background: theme.colors.bg, color: theme.colors.title }}><span style={{ background: theme.colors.accent }} /><b>{theme.name}</b><i style={{ background: theme.colors.accent }} /></div><strong>{theme.name}</strong><small>{theme.description}</small><em>{theme.family} · {theme.layout_count || 0} {t("coursewareAgent.theme.layouts")} · {theme.accessibility?.passes ? t("coursewareAgent.theme.highContrast") : t("coursewareAgent.theme.needsCheck")}</em></button>)}</div></section>;
}

function LayoutingStep({ progress, error, onRetry, onChooseTheme }: { progress: number; error?: string | null; onRetry: () => void; onChooseTheme: () => void }) {
  const { t } = useI18n();
  const phases: TranslationKey[] = ["coursewareAgent.layouting.phases.analyse", "coursewareAgent.layouting.phases.match", "coursewareAgent.layouting.phases.design", "coursewareAgent.layouting.phases.check"];
  return <section className="ppt-layout-step ppt-layouting-step"><div className="ppt-layouting-orb">✦</div><span className="ppt-kicker">AI LAYOUT ENGINE</span><h2>{error ? t("coursewareAgent.layouting.failedTitle") : t("coursewareAgent.layouting.title")}</h2><p>{error || t("coursewareAgent.layouting.subtitle")}</p><div className="ppt-layouting-progress"><div style={{ width: `${progress}%` }} /></div><div className="ppt-layouting-phases">{phases.map((phase, index) => <div key={phase} className={progress >= (index + 1) * 25 ? "done" : progress > index * 25 ? "active" : ""}><span>{progress >= (index + 1) * 25 ? "✓" : String(index + 1).padStart(2, "0")}</span><b>{t(phase)}</b></div>)}</div>{error && <div className="ppt-layouting-actions"><button className="ppt-primary" onClick={onRetry}>{t("coursewareAgent.layouting.retry")}</button><button className="ppt-ghost" onClick={onChooseTheme}>{t("coursewareAgent.layouting.backToTheme")}</button></div>}</section>;
}

function PreviewEditor({ pages, selected, onSelect, onSave, onReorder, saving }: { pages: PptPage[]; selected: number; onSelect: (index: number) => void; onSave: (page: PptPage, doc: PptDocument) => void; onReorder: (ids: string[]) => void; saving: boolean }) {
  const { t } = useI18n();
  const page = pages[selected];
  const [dragId, setDragId] = useState<string | null>(null);
  return <div className="ppt-rich-editor"><aside className="ppt-rich-thumbnails"><div className="ppt-thumb-head"><strong>{t("coursewareAgent.pages.title")}</strong><span>{t(pages.length === 1 ? "coursewareAgent.pages.count.one" : "coursewareAgent.pages.count.other", { count: pages.length })}</span></div><div className="ppt-thumb-list">{pages.map((item, i) => <div key={item.id} draggable onDragStart={() => setDragId(item.id)} onDragOver={(event) => event.preventDefault()} onDrop={() => { if (!dragId || dragId === item.id) return; const ids = pages.map((entry) => entry.id); const from = ids.indexOf(dragId); const to = ids.indexOf(item.id); ids.splice(from, 1); ids.splice(to, 0, dragId); onReorder(ids); setDragId(null); }}><SlideThumbnail page={{ ...item, sort_order: i }} selected={i === selected} onClick={() => onSelect(i)} /></div>)}</div></aside><main className="ppt-rich-main"><div className="ppt-rich-canvas"><SlideCanvas page={page} editable onChange={(doc) => page && onSave(page, doc)} /></div></main></div>;
}

/**
 * Drive one PPT project through the studio surfaces.
 */
export default function CoursewareAgent() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId?: string }>();
  const [projects, setProjects] = useState<PptProject[]>([]); const [active, setActive] = useState<PptProject | null>(null); const [pages, setPages] = useState<PptPage[]>([]); const [messages, setMessages] = useState<PptMessage[]>([]); const [requirement, setRequirement] = useState<PptRequirement | null>(null); const [sources, setSources] = useState<PptSource[]>([]); const [themes, setThemes] = useState<PptTheme[]>([]); const [selected, setSelected] = useState(0); const [surface, setSurface] = useState<Surface>("start"); const [loading, setLoading] = useState(false); const [outlineGenerating, setOutlineGenerating] = useState(false); const [visualRunning, setVisualRunning] = useState(false); const [layoutProgress, setLayoutProgress] = useState(0); const [layoutError, setLayoutError] = useState<string | null>(null); const page = pages[selected];
  const [agentOpen, setAgentOpen] = useState(false);
  const [projectLoading, setProjectLoading] = useState(Boolean(projectId)); const [deletingId, setDeletingId] = useState<string | null>(null); const [deleteCandidate, setDeleteCandidate] = useState<PptProject | null>(null); const [removingIds, setRemovingIds] = useState<Record<string, boolean>>({}); const [previewErrors, setPreviewErrors] = useState<Record<string, boolean>>({}); const [previewSources, setPreviewSources] = useState<Record<string, string>>({});
  const refresh = async (project = active) => { if (!project) return; const [p, ps, ms, req, src] = await Promise.all([pptApi.project(project.id), pptApi.pages(project.id), pptApi.messages(project.id), pptApi.requirements(project.id), pptApi.sources(project.id)]); setActive(p.data); setPages(ps.data.items.sort((a, b) => a.sort_order - b.sort_order)); setMessages(ms.data.items); setRequirement(req.data); setSources(src.data.items); };
  const refreshMessages = async (project = active) => { if (!project) return; const { data } = await pptApi.messages(project.id); setMessages(data.items); };
  useEffect(() => { pptApi.projects().then((r) => setProjects(r.data.items)).catch(() => undefined); pptApi.themes().then((r) => setThemes(r.data.items)).catch(() => undefined); }, []);
  useEffect(() => {
    let cancelled = false;
    const urls: string[] = [];
    const load = async () => {
      const entries = await Promise.all(projects.map(async (project) => {
        if (!project.cover_preview_url) return [project.id, ""] as const;
        try {
          const { data } = await pptApi.preview(project.cover_preview_url);
          const url = URL.createObjectURL(data);
          if (cancelled) { URL.revokeObjectURL(url); return [project.id, ""] as const; }
          urls.push(url);
          return [project.id, url] as const;
        } catch { return [project.id, ""] as const; }
      }));
      if (!cancelled) setPreviewSources(Object.fromEntries(entries));
    };
    void load();
    return () => { cancelled = true; urls.forEach((url) => URL.revokeObjectURL(url)); };
  }, [projects]);
  const generation = usePptGeneration({ projectId: active?.id, pageCount: pages.length, onComplete: async () => { await refresh(); setSelected(0); setSurface("editor"); } });
  useEffect(() => {
    let cancelled = false;
    if (!projectId) {
      setProjectLoading(false); setActive(null); setPages([]); setMessages([]); setRequirement(null); setSources([]); return () => { cancelled = true; };
    }
    setProjectLoading(true); setActive(null);
    pptApi.project(projectId).then(async ({ data }) => {
      if (cancelled) return;
      setSurface(data.page_count ? (data.latest_checkpoint_code ? "outline" : data.current_stage === "visual" ? "visual" : data.theme_id && data.design_status === "ready" ? "editor" : data.theme_id ? "theme" : "theme") : "start");
      await refresh(data);
    }).catch(() => { if (!cancelled) { toast.error(t("coursewareAgent.project.notFound")); navigate("/teacher/courseware-agent", { replace: true }); } }).finally(() => { if (!cancelled) setProjectLoading(false); });
    return () => { cancelled = true; };
  }, [projectId]);
  const openProject = (project: PptProject) => navigate(`/teacher/courseware-agent/${project.id}`);
  const uploadFiles = async (files: FileList | File[], project = active) => { if (!project) return; setLoading(true); try { for (const file of Array.from(files)) await pptApi.upload(project.id, file); await refresh(project); toast.success(t("coursewareAgent.project.materialsAdded")); } catch (e: any) { toast.error(e.response?.data?.detail || t("coursewareAgent.project.materialsUploadFailed")); } finally { setLoading(false); } };
  const create = async (text: string, files: File[] = []) => { if (!text.trim()) return; setLoading(true); try { const { data } = await pptApi.createProject({ title: text.trim().slice(0, 32), request_text: text.trim() }); setProjects((items) => [data, ...items]); openProject(data); if (files.length) await uploadFiles(files, data); } catch (e: any) { toast.error(e.response?.data?.detail || t("coursewareAgent.project.createFailed")); } finally { setLoading(false); } };
  const removeProject = async (event: React.MouseEvent, project: PptProject) => { event.stopPropagation(); if (deletingId) return; setDeleteCandidate(project); };
  const confirmRemoveProject = async () => { const project = deleteCandidate; if (!project || deletingId) return; setDeletingId(project.id); try { await pptApi.deleteProject(project.id); setDeleteCandidate(null); setRemovingIds((items) => ({ ...items, [project.id]: true })); window.setTimeout(() => { setProjects((items) => items.filter((item) => item.id !== project.id)); setRemovingIds((items) => { const next = { ...items }; delete next[project.id]; return next; }); }, 420); toast.success(t("coursewareAgent.project.deleted")); if (projectId === project.id) navigate("/teacher/courseware-agent", { replace: true }); } catch (e: any) { toast.error(e.response?.data?.detail || t("coursewareAgent.project.deleteFailed")); } finally { setDeletingId(null); } };
  const generateOutline = async () => { if (!active || !requirement?.ready_to_outline) return; setLoading(true); setOutlineGenerating(true); setSurface("outline"); try { await pptApi.generateOutline(active.id, { page_count_target: active.page_count_target || requirement.page_count_target || 10 }); await refresh(); toast.success(t("coursewareAgent.outline.generated")); } catch (e: any) { toast.error(e.response?.data?.detail || t("coursewareAgent.outline.generateFailed")); setSurface("start"); } finally { setOutlineGenerating(false); setLoading(false); } };
  const generateDesign = async () => { if (!active || generation.running) return; setLoading(true); setLayoutError(null); setSurface("layouting"); await generation.generate(); setLoading(false); };
  const autosave = usePptAutosave({
    projectId: active?.id,
    save: async (pending) => (await pptApi.patchDocument(pending.projectId, pending.pageId, pending.document, pending.revision)).data,
    onSaved: (data) => setPages((items) => items.map((item) => item.id === data.id ? data : item)),
    onError: (error) => { toast.error(getApiErrorMessage(error, t("coursewareAgent.editor.saveFailed"))); void refresh(); },
  });
  const reorderPages = async (ids: string[]) => {
    if (!active) return;
    const selectedPageId = pages[selected]?.id;
    try {
      const { data } = await pptApi.patchStoryboard(active.id, ids);
      const nextPages = [...data.items].sort((a, b) => a.sort_order - b.sort_order);
      setPages(nextPages);
      const nextSelected = selectedPageId ? nextPages.findIndex((item) => item.id === selectedPageId) : 0;
      setSelected(nextSelected >= 0 ? nextSelected : 0);
    } catch (e: any) { toast.error(e.response?.data?.detail || t("coursewareAgent.editor.orderSaveFailed")); }
  };
  const confirmOutline = async () => { if (!active) return; try { await pptApi.confirmCheckpoint(active.id, "outline_confirm"); await refresh(); setSurface("visual"); toast.success(t("coursewareAgent.outline.confirmed")); } catch (e: any) { toast.error(e.response?.data?.detail || t("coursewareAgent.outline.confirmFirst")); } };
  const runVisualResearch = async () => { if (!active) return; setVisualRunning(true); try { const { data } = await pptApi.batch(active.id, "project_batch_visual"); const job = data?.id ? data : data?.result; await refresh(); toast.success(job?.id ? t("coursewareAgent.visual.backgroundStarted") : t("coursewareAgent.visual.submitted")); if (job?.id) { const timer = window.setInterval(async () => { try { const { data: state } = await pptApi.generationJob(active.id, job.id); await refresh(); if (["completed", "completed_with_errors", "failed", "cancelled"].includes(state.status)) { window.clearInterval(timer); setVisualRunning(false); toast[state.status === "completed" ? "success" : "error"](state.status === "completed" ? t("coursewareAgent.visual.completed") : state.status === "completed_with_errors" ? t("coursewareAgent.visual.completedWithErrors") : t("coursewareAgent.visual.failedRetry")); } } catch { window.clearInterval(timer); setVisualRunning(false); } }, 1200); } else setVisualRunning(false); } catch (e: any) { setVisualRunning(false); toast.error(e.response?.data?.detail || t("coursewareAgent.visual.failed")); } };
  const saveVisualSelection = async (target: PptPage, ids: string[]) => { if (!active) return; try { const { data } = await pptApi.saveVisualSelection(active.id, target.id, ids); setPages((items) => items.map((item) => item.id === data.id ? data : item)); toast.success(t("coursewareAgent.visual.selectionSaved")); } catch (e: any) { toast.error(e.response?.data?.detail || t("coursewareAgent.visual.selectionSaveFailed")); } };
  if (!projectId) return (
    <div className="ppt-immersive-home">
      <div className="ppt-home-layout">
          <div className="ppt-home-main">
            <WelcomeBanner className="ppt-home-agent-banner" eyebrow={t("coursewareAgent.home.eyebrow")} title={<>{t("coursewareAgent.home.welcomeTitle")}<br /><em>{t("coursewareAgent.home.welcomeTitleAccent")}</em></>} subtitle={t("coursewareAgent.home.welcomeSubtitle")} />
            <Composer onCreate={create} loading={loading} />
          </div>
          <div className="ppt-recent"><div className="ppt-recent-head"><div><span className="ppt-kicker">PROJECTS</span><h2>{t("coursewareAgent.home.recentTitle")}</h2></div><span>{t(projects.length === 1 ? "coursewareAgent.home.projectCount.one" : "coursewareAgent.home.projectCount.other", { count: projects.length })}</span></div><div className="ppt-recent-grid">
            {projects.map((project) => <article key={project.id} className={`ppt-recent-card ${removingIds[project.id] ? "is-removing" : ""}`}><button type="button" className="ppt-recent-card-main" onClick={() => openProject(project)}><div className="ppt-mini-preview">{previewSources[project.id] && !previewErrors[project.id] ? <img src={previewSources[project.id]} alt={t("coursewareAgent.home.coverAlt", { title: project.title })} onError={() => setPreviewErrors((items) => ({ ...items, [project.id]: true }))} /> : <div className="ppt-mini-fallback"><span>{stageLabel(project.current_stage, t)}</span><b>{project.page_count || "—"}</b></div>}</div><strong>{project.title}</strong><small>{project.request_text}</small></button><button type="button" className="ppt-project-delete" onClick={(event) => void removeProject(event, project)} disabled={deletingId === project.id} aria-label={t("coursewareAgent.home.deleteProjectAria", { title: project.title })} title={t("coursewareAgent.home.deleteProject")}><i className="fas fa-trash" /></button></article>)}
            {!projects.length && <div className="ppt-recent-empty">{t("coursewareAgent.home.empty")}</div>}
          </div></div>
      </div>
      <HKUConfirmDialog open={Boolean(deleteCandidate)} scope="surface" eyebrow="DELETE PROJECT" title={t("coursewareAgent.home.deleteTitle")} description={deleteCandidate ? t("coursewareAgent.home.deleteDescription", { title: deleteCandidate.title }) : undefined} icon={<i className="fas fa-trash" />} onClose={() => { if (!deletingId) setDeleteCandidate(null); }} onConfirm={confirmRemoveProject} confirmLabel={t("coursewareAgent.home.deleteConfirm")} loading={Boolean(deletingId)} labelledBy="ppt-delete-title" />
    </div>
  );
  if (projectLoading || !active) return <div className="ppt-project-loading">{t("coursewareAgent.project.loading")}</div>;
  return <div className="ppt-immersive-shell">
    <ProjectSidebar active={active} surface={surface} pages={pages} selected={selected} onSurface={setSurface} onSelectPage={(index) => { setSelected(index); setSurface("editor"); }} />
    <div className="ppt-immersive-body">
      <header className="ppt-immersive-header"><div className="ppt-project-title"><span className="ppt-kicker">{surface === "editor" && page ? "PREVIEW & EDIT" : "PPT STUDIO · WORKSPACE"}</span><strong>{surface === "editor" && page ? page.title : active.title}</strong></div><div className="ppt-header-actions">{surface === "editor" && page && <button className="ppt-header-save" disabled={autosave.saving}>{autosave.saving ? t("coursewareAgent.header.saving") : t("coursewareAgent.header.autoSaved")}</button>}{pages.length > 0 && <button onClick={() => setSurface("present")} className="ppt-ghost">{t("coursewareAgent.header.present")}</button>}<button className="ppt-primary" disabled={!pages.some((p) => !!p.document)} onClick={async () => { try { const { data } = await pptApi.export(active.id); toast.success(t("coursewareAgent.header.exportStarted")); const poll = window.setInterval(async () => { try { const status = await pptApi.exportStatus(active.id, data.id); if (status.data.status === "completed") { window.clearInterval(poll); const response = await pptApi.downloadExport(active.id, data.id); const url = URL.createObjectURL(response.data); const link = document.createElement("a"); link.href = url; link.download = "courseware.pptx"; document.body.appendChild(link); link.click(); link.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); } else if (status.data.status === "failed") { window.clearInterval(poll); toast.error(status.data.error || t("coursewareAgent.header.exportFailed")); } } catch { /* keep polling */ } }, 1200); } catch (e: unknown) { toast.error(getApiErrorMessage(e, t("coursewareAgent.header.exportFailed"))); } }}>{t("coursewareAgent.header.export")}</button></div></header>
      {surface === "start" && <div className="ppt-start-grid"><Chat project={active} messages={messages.filter((m) => !m.page_id)} requirement={requirement} sources={sources} onRequirementUpdate={(response) => setRequirement((current) => ({ ...(current || {}), ...response }))} onUpload={(files) => void uploadFiles(files)} onSent={() => void refreshMessages()} /><section className={`ppt-start-brief ${requirement?.brief_summary ? "is-ready" : ""}`}><span className="ppt-kicker">PROJECT BRIEF</span><h2>{requirement?.brief_summary ? t("coursewareAgent.start.briefTitle") : t("coursewareAgent.start.clarifyTitle")}</h2><p>{requirement?.brief_summary || active.request_text}</p><div className="ppt-brief-points"><div><b>01</b><span>{requirement?.answers?.audience || t("coursewareAgent.start.audiencePending")}</span></div><div><b>02</b><span>{requirement?.answers?.goals || t("coursewareAgent.start.goalsPending")}</span></div><div><b>03</b><span>{requirement?.answers?.duration || requirement?.answers?.slide_count || t("coursewareAgent.start.pacingPending")}</span></div></div>{requirement?.suggested_additions?.length ? <p className="ppt-extra-hint">{t("coursewareAgent.start.extras", { items: requirement.suggested_additions.join(t("coursewareAgent.start.extrasSeparator")) })}</p> : null}<button className="ppt-primary wide" onClick={() => void generateOutline()} disabled={loading || !requirement?.ready_to_outline}>{loading ? t("coursewareAgent.start.generating") : requirement?.ready_to_outline ? t("coursewareAgent.start.generate") : t("coursewareAgent.start.completeChat")}</button></section></div>}
      {surface === "outline" && <div className="ppt-workspace-grid">{outlineGenerating ? <section className="ppt-outline-generating"><div className="ppt-layouting-orb">✦</div><span className="ppt-kicker">OUTLINE ENGINE</span><h2>{t("coursewareAgent.outlineEngine.title")}</h2><p>{t("coursewareAgent.outlineEngine.subtitle")}</p><div className="ppt-outline-loading-bar"><i /></div></section> : <OutlineBoard pages={pages} onSelect={(item) => { setSelected(pages.findIndex((p) => p.id === item.id)); }} onUpdate={async (item, payload) => { const { data } = await pptApi.patchPage(active.id, item.id, payload); setPages((items) => items.map((current) => current.id === data.id ? data : current)); return data; }} onReorder={(ids) => { void pptApi.patchStoryboard(active.id, ids).then(() => refresh()); }} onConfirm={() => void confirmOutline()} />}<Chat project={active} page={page} messages={messages.filter((m) => !m.page_id || m.page_id === page?.id)} onSent={() => void refresh()} /></div>}
      {surface === "visual" && <VisualStep pages={pages} running={visualRunning} onRun={() => void runVisualResearch()} onContinue={() => setSurface("theme")} onSave={saveVisualSelection} />}
      {surface === "theme" && <ThemeStep themes={themes} selected={active.theme_id} onSelect={async (themeId) => { if (loading) return; try { const { data } = await pptApi.selectTheme(active.id, themeId); setActive(data); await generateDesign(); } catch (e: any) { setLayoutError(e.response?.data?.detail || t("coursewareAgent.theme.saveFailed")); setSurface("layouting"); } }} disabled={loading} />}
      {surface === "layouting" && <LayoutingStep progress={generation.progress} error={generation.error || layoutError} onRetry={() => void generateDesign()} onChooseTheme={() => { setLayoutError(null); setSurface("theme"); }} />}
      {surface === "editor" && page && <div className="ppt-editor-grid"><main className="ppt-editor-main"><PreviewEditor pages={pages} selected={selected} onSelect={setSelected} onReorder={(ids) => void reorderPages(ids)} onSave={(target, doc) => autosave.schedule(target, doc)} saving={autosave.saving} /></main><AgentDialog open={agentOpen} onClose={() => setAgentOpen(false)} pageNumber={page.sort_order + 1}><Chat project={active} page={page} messages={messages.filter((m) => m.page_id === page.id)} onBeforeAgent={autosave.flush} onAgentSlideFocus={setSelected} onSent={() => refresh()} /></AgentDialog><AgentFab open={agentOpen} onClick={() => setAgentOpen((value) => !value)} /></div>}
      {surface === "present" && pages.length > 0 && <Presentation pages={pages} index={selected} onIndexChange={setSelected} onClose={() => setSurface("editor")} />}
    </div>
  </div>;
}

function ProjectSidebar({ active, surface, pages, selected, onSurface, onSelectPage }: { active: PptProject; surface: Surface; pages: PptPage[]; selected: number; onSurface: (surface: Surface) => void; onSelectPage: (index: number) => void }) {
  const { t } = useI18n();
  const steps: { key: Surface; icon: string; label: TranslationKey; disabled?: boolean }[] = [
    { key: "start", icon: "✦", label: "coursewareAgent.sidebar.steps.chat" },
    { key: "outline", icon: "▦", label: "coursewareAgent.sidebar.steps.storyboard", disabled: !pages.length },
    { key: "visual", icon: "◌", label: "coursewareAgent.sidebar.steps.visual", disabled: !pages.length },
    { key: "theme", icon: "◉", label: "coursewareAgent.sidebar.steps.theme", disabled: !pages.length },
    { key: "editor", icon: "◈", label: "coursewareAgent.sidebar.steps.editor", disabled: !pages.some((item) => !!item.document) },
  ];
  const currentIndex = Math.max(0, steps.findIndex((step) => step.key === surface));
  return <aside className="ppt-project-sidebar"><div className="ppt-sidebar-brand"><span>HKU</span><div><b>{t("coursewareAgent.sidebar.brand")}</b><small>PROJECT WORKSPACE</small></div></div><div className="ppt-sidebar-project"><span className="ppt-kicker">{t("coursewareAgent.sidebar.currentProject")}</span><strong>{active.title}</strong><small>{t((active.page_count || 0) === 1 ? "coursewareAgent.pages.count.one" : "coursewareAgent.pages.count.other", { count: active.page_count || 0 })} · {stageLabel(active.current_stage, t)}</small></div><nav className="ppt-project-nav" aria-label={t("coursewareAgent.sidebar.navigation")}>{steps.map((step, index) => <button key={step.key} className={`${surface === step.key ? "active" : ""} ${index < currentIndex ? "completed" : ""}`} onClick={() => onSurface(step.key)} disabled={step.disabled}><span className="ppt-step-icon">{step.icon}</span><span className="ppt-step-label">{t(step.label)}</span><span className="ppt-step-arrow" aria-hidden="true">{index < currentIndex ? "✓" : "→"}</span></button>)}</nav>{pages.length > 0 && surface !== "editor" && <div className="ppt-sidebar-pages"><div><span>{t("coursewareAgent.pages.title")}</span><small>{t(pages.length === 1 ? "coursewareAgent.pages.count.one" : "coursewareAgent.pages.count.other", { count: pages.length })}</small></div>{pages.map((item, index) => <button key={item.id} className={selected === index ? "active" : ""} onClick={() => onSelectPage(index)}><span>{String(index + 1).padStart(2, "0")}</span><b>{item.title || t("coursewareAgent.sidebar.untitledPage")}</b></button>)}</div>}<div className="ppt-sidebar-footer">{t("coursewareAgent.sidebar.footer")}</div></aside>;
}


function Composer({ onCreate, loading }: { onCreate: (text: string, files: File[]) => void; loading: boolean }) { const { t } = useI18n(); const [text, setText] = useState(""); const [files, setFiles] = useState<File[]>([]); return <div className="ppt-home-composer"><textarea value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onCreate(text, files); } }} placeholder={t("coursewareAgent.composer.placeholder")} rows={3} /><div className={`ppt-home-files ${files.length ? "has-files" : ""}`}>{files.length ? files.map((file) => <span key={`${file.name}-${file.lastModified}`}>📎 {file.name}<button type="button" onClick={() => setFiles((items) => items.filter((item) => item !== file))}>×</button></span>) : <span className="ppt-home-files-placeholder"><i className="fas fa-paperclip" /> {t("coursewareAgent.composer.attachmentsHint")}</span>}</div><div><label className="ppt-upload-button">{t("coursewareAgent.composer.addMaterials")}<input type="file" multiple accept=".pdf,.pptx,.docx,.xlsx,.xls,.txt,.md,.markdown,.csv,.json,image/png,image/jpeg,image/webp" onChange={(e) => setFiles((items) => [...items, ...Array.from(e.target.files || [])])} /></label><small>{t("coursewareAgent.composer.sendHint")}</small><button onClick={() => onCreate(text, files)} disabled={loading || !text.trim()}>{loading ? t("coursewareAgent.composer.creating") : t("coursewareAgent.composer.create")}</button></div></div>; }
function Presentation({ pages, index, onIndexChange, onClose }: { pages: PptPage[]; index: number; onIndexChange: (index: number) => void; onClose: () => void }) {
  const { t } = useI18n();
  const page = pages[index];
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const updateScale = () => {
      // Reserve room for the navigation buttons and their gaps, then fit the
      // 1280x720 slide into the remaining area in both dimensions.
      const availableWidth = Math.max(0, stage.clientWidth - 132);
      const availableHeight = Math.max(0, stage.clientHeight - 8);
      setScale(Math.min(1, availableWidth / SLIDE_WIDTH, availableHeight / SLIDE_HEIGHT));
    };
    const observer = new ResizeObserver(updateScale);
    observer.observe(stage);
    updateScale();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowLeft") onIndexChange(Math.max(0, index - 1));
      if (event.key === "ArrowRight") onIndexChange(Math.min(pages.length - 1, index + 1));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [index, onClose, onIndexChange, pages.length]);

  const slideWidth = SLIDE_WIDTH * scale;
  const slideHeight = SLIDE_HEIGHT * scale;
  return <div className="ppt-presentation">
    <button className="ppt-presentation-close" onClick={onClose} aria-label={t("coursewareAgent.presentation.exit")}>×</button>
    <div className="ppt-presentation-title"><span>{t("coursewareAgent.presentation.previewTitle")}</span><strong>{page.title}</strong></div>
    <div className="ppt-presentation-stage" ref={stageRef}>
      <button aria-label={t("coursewareAgent.presentation.previous")} disabled={index === 0} onClick={() => onIndexChange(Math.max(0, index - 1))}>‹</button>
      <div className="ppt-rendered-slide" style={{ width: slideWidth, height: slideHeight }}>
        <div className="ppt-present-scale" style={{ width: SLIDE_WIDTH, height: SLIDE_HEIGHT, transform: `scale(${scale})` }}><SlideRenderer document={editableDocument(page)} /></div>
      </div>
      <button aria-label={t("coursewareAgent.presentation.next")} disabled={index === pages.length - 1} onClick={() => onIndexChange(Math.min(pages.length - 1, index + 1))}>›</button>
    </div>
    <div className="ppt-presentation-footer">{index + 1} / {pages.length}<span>{t("coursewareAgent.presentation.footerHint")}</span></div>
  </div>;
}
