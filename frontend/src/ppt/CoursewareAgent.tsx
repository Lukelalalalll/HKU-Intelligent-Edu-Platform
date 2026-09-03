import React, { useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";
import { PptChatStreamEvent, PptDocument, PptMessage, PptPage, PptProject, PptSlideElement, PptRequirement, PptSource, PptTheme, pptApi } from "../api";
import { SLIDE_HEIGHT, SLIDE_WIDTH, SlideRenderer, SlideThumbnail, editableDocument } from "./SlideRenderer";
import { HKUConfirmDialog } from "../shared/components/HKUDialog";
import WelcomeBanner from "../shared/components/WelcomeBanner";

type Surface = "start" | "outline" | "theme" | "layouting" | "editor" | "present";
const stageLabels: Record<string, string> = { init: "需求", outline: "大纲", theme: "主题", layout: "AI 排版", design: "预览", export: "完成" };
const deepseekModels = ["deepseek-v4-flash", "deepseek-v4-pro", "deepseek-v4-flash-vision-exp"];

function StudioRail({ surface, onNavigate }: { surface: Surface; onNavigate: (surface: Surface) => void }) {
  return <aside className="ppt-studio-rail" aria-label="课件工作区导航">
    <div className="ppt-rail-mark">✦</div>
    <button className={surface === "start" ? "active" : ""} onClick={() => onNavigate("start")} title="对话"><span>◌</span><small>对话</small></button>
    <button className={surface === "outline" ? "active" : ""} onClick={() => onNavigate("outline")} title="故事板"><span>▤</span><small>故事板</small></button>
    <button className={surface === "editor" ? "active" : ""} onClick={() => onNavigate("editor")} title="编辑器"><span>◫</span><small>编辑</small></button>
    <button className={surface === "present" ? "active" : ""} onClick={() => onNavigate("present")} title="放映"><span>▷</span><small>放映</small></button>
    <div className="ppt-rail-spacer" />
    <button title="帮助"><span>?</span><small>帮助</small></button>
  </aside>;
}

function StudioHomeHeader() {
  return <header className="ppt-studio-home-header"><div className="ppt-studio-home-logo"><b>HKU</b><span>INTELLIGENT EDU</span></div><div className="ppt-studio-home-context">课件工作台 <i /> 对话驱动创作</div><div className="ppt-studio-home-actions"><button title="快捷键">⌘ /</button><button title="通知">◔</button><div className="ppt-studio-avatar">T</div></div></header>;
}

function SlideCanvas({ page, editable, onChange }: { page: PptPage; editable: boolean; onChange?: (doc: PptDocument) => void }) {
  const [doc, setDoc] = useState<PptDocument>(() => editableDocument(page)); const [selectedId, setSelectedId] = useState<string | null>(null);
  const [history, setHistory] = useState<PptDocument[]>([]); const [future, setFuture] = useState<PptDocument[]>([]);
  const [scale, setScale] = useState(1); const viewportRef = useRef<HTMLDivElement | null>(null); const surfaceRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{ id: string; x: number; y: number; w: number; h: number; startX: number; startY: number; resize?: boolean } | null>(null);
  useEffect(() => setDoc(editableDocument(page)), [page.id, page.document, page.title, page.bullets]);
  useEffect(() => { const node = viewportRef.current; if (!node) return; const observer = new ResizeObserver(() => { const width = Math.max(320, node.clientWidth - 32); const height = Math.max(180, node.clientHeight - 72); setScale(Math.min(width / SLIDE_WIDTH, height / SLIDE_HEIGHT, 1)); }); observer.observe(node); return () => observer.disconnect(); }, []);
  const commit = (next: PptDocument, record = true) => { if (record) { setHistory((items) => [...items.slice(-19), doc]); setFuture([]); } setDoc(next); onChange?.(next); };
  const updateElement = (id: string, patch: Partial<PptSlideElement>) => commit({ ...doc, elements: doc.elements.map((el) => el.id === id ? { ...el, ...patch } : el) });
  const undo = () => { const previous = history[history.length - 1]; if (!previous) return; setHistory((items) => items.slice(0, -1)); setFuture((items) => [doc, ...items]); commit(previous, false); };
  const redo = () => { const next = future[0]; if (!next) return; setFuture((items) => items.slice(1)); setHistory((items) => [...items, doc]); commit(next, false); };
  const startDrag = (event: React.PointerEvent<HTMLDivElement>, element: PptSlideElement) => { dragRef.current = { id: element.id, x: element.x, y: element.y, w: element.w, h: element.h, startX: event.clientX, startY: event.clientY }; event.currentTarget.setPointerCapture?.(event.pointerId); };
  const moveDrag = (event: React.PointerEvent<HTMLDivElement>) => { const drag = dragRef.current; const surface = surfaceRef.current; if (!drag || !surface) return; const rect = surface.getBoundingClientRect(); const dx = ((event.clientX - drag.startX) / rect.width) * 100; const dy = ((event.clientY - drag.startY) / rect.height) * 100; updateElement(drag.id, drag.resize ? { w: Math.max(4, Math.min(100 - drag.x, drag.w + dx)), h: Math.max(4, Math.min(100 - drag.y, drag.h + dy)) } : { x: Math.max(0, Math.min(100 - drag.w, drag.x + dx)), y: Math.max(0, Math.min(100 - drag.h, drag.y + dy)) }); };
  return <div className="ppt-canvas-frame" ref={viewportRef} onKeyDown={(e) => { if (!editable) return; if (e.key === "Escape") setSelectedId(null); if (e.key === "Delete" && selectedId) { e.preventDefault(); commit({ ...doc, elements: doc.elements.filter((el) => el.id !== selectedId) }); setSelectedId(null); } if (!(e.ctrlKey || e.metaKey)) return; if (e.key.toLowerCase() === "z") { e.preventDefault(); undo(); } if (e.key.toLowerCase() === "y") { e.preventDefault(); redo(); } }} tabIndex={0} onPointerMove={moveDrag} onPointerUp={() => { dragRef.current = null; }} onPointerCancel={() => { dragRef.current = null; }}>
    <div className="ppt-canvas-viewport" style={{ width: SLIDE_WIDTH * scale, height: SLIDE_HEIGHT * scale }}><div className="ppt-canvas-scale" ref={surfaceRef} style={{ width: SLIDE_WIDTH, height: SLIDE_HEIGHT, transform: `scale(${scale})` }}><SlideRenderer document={doc} editable={editable} selectedId={selectedId} onSelect={(element) => setSelectedId(element.id)} onPointerDown={startDrag} onTextBlur={(element, text) => updateElement(element.id, { text })} onResizeStart={(event, element) => { event.stopPropagation(); dragRef.current = { id: element.id, x: element.x, y: element.y, w: element.w, h: element.h, startX: event.clientX, startY: event.clientY, resize: true }; event.currentTarget.setPointerCapture?.(event.pointerId); }} /></div></div>
    <div className="ppt-canvas-controls">{editable && <><button onClick={undo} disabled={!history.length}>撤销</button><button onClick={redo} disabled={!future.length}>重做</button>{selectedId && <button onClick={() => { commit({ ...doc, elements: doc.elements.filter((el) => el.id !== selectedId) }); setSelectedId(null); }}>删除元素</button>}</>}</div>
  </div>;
}

function Chat({ project, page, messages, requirement, sources, onSent, onUpload, onBeforeAgent, onAgentSlideFocus, onRequirementUpdate }: { project: PptProject; page?: PptPage; messages: PptMessage[]; requirement?: PptRequirement | null; sources?: PptSource[]; onSent: () => void | Promise<void>; onUpload?: (files: FileList) => void; onBeforeAgent?: () => Promise<void>; onAgentSlideFocus?: (index: number) => void; onRequirementUpdate?: (response: any) => void }) {
  const [value, setValue] = useState(""); const [sending, setSending] = useState(false); const [streamText, setStreamText] = useState(""); const [activities, setActivities] = useState<PptChatStreamEvent[]>([]); const [optimistic, setOptimistic] = useState<PptMessage | null>(null); const abortRef = useRef<AbortController | null>(null); const streamRef = useRef<HTMLDivElement | null>(null);
  const lastAssistant = [...messages].reverse().find((item) => item.role === "assistant");
  const question = !page ? (lastAssistant?.payload?.question || requirement?.questions?.[0]) : null;
  useEffect(() => () => abortRef.current?.abort(), []);
  const send = async (content = value.trim(), option?: string) => {
    if ((!content && !option) || sending) return;
    const text = content || option || "";
    setSending(true); setValue(""); setStreamText(""); setActivities([]); setOptimistic({ id: `optimistic-${Date.now()}`, role: "user", stage: page ? "editor" : "init", scope_type: page ? "page" : "project", page_id: page?.id, content_md: text, payload: {}, created_at: new Date().toISOString() });
    if (!page) { const controller = new AbortController(); abortRef.current = controller; try { const complete = await pptApi.streamRequirementChat(project.id, { content: text, option_id: option, option_label: option }, { onEvent: (event) => { if (event.type === "chunk") setStreamText((current) => current + (event.chunk || "")); if (event.type === "complete" && event.requirement) onRequirementUpdate?.(event.requirement); } }, controller.signal); if (complete?.requirement) onRequirementUpdate?.(complete.requirement); await onSent(); } catch (e: any) { if (e?.name !== "AbortError") toast.error(e.response?.data?.detail || e.message || "消息发送失败"); } finally { abortRef.current = null; setSending(false); setOptimistic(null); setStreamText(""); } return; }
    const controller = new AbortController(); abortRef.current = controller;
    try {
      await onBeforeAgent?.();
      await pptApi.streamMessage(project.id, { content: text, page_id: page.id, ui_surface: "editor" }, { onEvent: (event) => { if (event.type === "chunk") setStreamText((current) => current + (event.chunk || "")); if (event.type === "trace") { setActivities((current) => [...current, event]); const target = event.trace?.slideIndex; if (typeof target === "number" && target >= 0) onAgentSlideFocus?.(target); } } }, controller.signal);
      await onSent();
    } catch (e: any) { if (e?.name !== "AbortError") toast.error(e.response?.data?.detail || e.message || "消息发送失败"); } finally { abortRef.current = null; setSending(false); setActivities([]); setStreamText(""); }
  };
  const stop = () => { abortRef.current?.abort(); abortRef.current = null; setSending(false); };
  useEffect(() => { const node = streamRef.current; if (node) node.scrollTop = node.scrollHeight; }, [messages, streamText, optimistic]);
  return <section className="ppt-conversation"><div className="ppt-conversation-head"><div><span className="ppt-kicker">AI 课件协作</span><strong>{page ? `正在讨论：第 ${page.sort_order + 1} 页` : "先聊清楚，再开始生成"}</strong></div><span className="ppt-online"><i /> 在线</span></div><div className="ppt-conversation-stream" ref={streamRef}>{messages.length || optimistic ? <>{messages.map((message) => <div key={message.id} className={`ppt-message ppt-message-enter ${message.role === "user" ? "user" : "assistant"}`}><div>{message.content_md}</div>{message.payload?.action_type && <small>已执行：{message.payload.action_type}</small>}</div>)}{optimistic && <div className="ppt-message user ppt-message-enter ppt-message-pending"><div>{optimistic.content_md}</div><small>发送中…</small></div>}</> : <div className="ppt-chat-empty"><div className="ppt-chat-orb">✦</div><h3>告诉我你要讲什么</h3><p>我会先追问受众、时长和重点，再把讨论整理成可确认的大纲。</p></div>}{sending && <div className="ppt-message assistant ppt-agent-live ppt-message-enter"><div>{streamText || "正在理解你的需求…"}<span className="ppt-typing-caret" /></div>{activities.map((event, index) => <small key={`${event.trace?.tool}-${index}`}>{event.trace?.status === "success" ? "✓" : event.trace?.status === "error" ? "!" : "⋯"} {event.trace?.message || event.status}</small>)}</div>}{!page && question?.options?.length ? <div className="ppt-requirement-options">{question.options.map((option: string) => <button key={option} onClick={() => void send("", option)} disabled={sending}>{option}</button>)}</div> : null}{!page && sources?.length ? <div className="ppt-attachment-list">{sources.map((source) => <span key={source.id}>📎 {source.title}</span>)}</div> : null}</div><div className="ppt-composer"><textarea value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }} placeholder={page ? "告诉 Agent 如何修改当前页…" : "补充你的需求，或点击上方选项…"} rows={3} disabled={sending} /><div className="ppt-composer-tools">{onUpload && <label className="ppt-upload-button">＋ 资料<input type="file" multiple accept=".pdf,.md,.markdown,image/png,image/jpeg,image/webp" onChange={(e) => { if (e.target.files?.length) onUpload(e.target.files); e.currentTarget.value = ""; }} /></label>}{sending ? <button onClick={stop} aria-label="停止">■</button> : <button onClick={() => void send()} disabled={!value.trim()} aria-label="发送">↑</button>}</div><small>Enter 发送 · Shift + Enter 换行 · 支持 PDF、Markdown、图片</small></div></section>;
}

function ProviderSettings() {
  const [config, setConfig] = useState({ base_url: "https://api.deepseek.com", api_key: "", model: "deepseek-v4-flash", embedding_model: "", timeout_seconds: 120 });
  const [configuredKey, setConfiguredKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    pptApi.provider().then(({ data }) => {
      setConfig({ base_url: data.base_url, api_key: "", model: data.model, embedding_model: data.embedding_model, timeout_seconds: data.timeout_seconds });
      setConfiguredKey(data.api_key_masked);
    }).catch(() => toast.error("模型配置读取失败")).finally(() => setLoading(false));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await pptApi.saveProvider({ ...config, timeout_seconds: Number(config.timeout_seconds), ...(config.api_key.trim() ? { api_key: config.api_key.trim() } : {}) });
      const { data } = await pptApi.provider();
      setConfiguredKey(data.api_key_masked);
      setConfig((current) => ({ ...current, api_key: "" }));
      toast.success("课件 Agent 配置已保存");
    } catch (error: any) { toast.error(error.response?.data?.detail || "配置保存失败"); }
    finally { setSaving(false); }
  };

  const test = async () => {
    setTesting(true);
    try { await pptApi.testProvider(); toast.success("连接测试成功"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "连接测试失败"); }
    finally { setTesting(false); }
  };

  const clear = async () => {
    if (!window.confirm("清除后，课件 Agent 将无法调用模型，确定继续吗？")) return;
    try { await pptApi.clearProvider(); setConfiguredKey(""); setConfig((current) => ({ ...current, api_key: "" })); toast.success("课件 Agent 配置已清除"); }
    catch (error: any) { toast.error(error.response?.data?.detail || "配置清除失败"); }
  };

  return <aside className="ppt-provider-card" aria-label="课件 Agent 模型配置">
    <div className="ppt-provider-heading"><div className="ppt-provider-icon">✦</div><div><span className="ppt-kicker">AI PROVIDER</span><h2>课件 Agent 配置</h2></div><span className={`ppt-provider-status ${configuredKey ? "is-ready" : ""}`}><i />{configuredKey ? "已配置" : "未配置"}</span></div>
    <p className="ppt-provider-description">配置仅用于课件 Agent 的生成、对话与编辑，不会影响平台其他 AI 业务。</p>
    {loading ? <div className="ppt-provider-loading">正在读取配置…</div> : <div className="ppt-provider-form">
      <label>API Base URL<input value={config.base_url} onChange={(e) => setConfig((current) => ({ ...current, base_url: e.target.value }))} placeholder="https://api.deepseek.com" /></label>
      <label>API Key<div className="ppt-provider-key-wrap"><input type={showKey ? "text" : "password"} value={config.api_key} onChange={(e) => setConfig((current) => ({ ...current, api_key: e.target.value }))} placeholder={configuredKey ? `已保存：${configuredKey}` : "粘贴你的 API Key"} autoComplete="off" /><button type="button" onClick={() => setShowKey((value) => !value)} aria-label={showKey ? "隐藏 API Key" : "显示 API Key"}>{showKey ? "隐藏" : "显示"}</button></div></label>
      <div className="ppt-provider-field-row"><label>模型<input list="deepseek-model-options" value={config.model} onChange={(e) => setConfig((current) => ({ ...current, model: e.target.value }))} /><datalist id="deepseek-model-options">{deepseekModels.map((model) => <option key={model} value={model} />)}</datalist><small>可选：Flash、Pro；Vision-Exp 支持图片输入</small></label><label>超时（秒）<input type="number" min={10} max={600} value={config.timeout_seconds} onChange={(e) => setConfig((current) => ({ ...current, timeout_seconds: Number(e.target.value) || 120 }))} /></label></div>
      <label>Embedding 模型（可选）<input value={config.embedding_model} onChange={(e) => setConfig((current) => ({ ...current, embedding_model: e.target.value }))} placeholder="DeepSeek 暂不提供 Embedding，可留空" /></label>
      <div className="ppt-provider-actions"><button className="ppt-primary" type="button" onClick={() => void save()} disabled={saving}>{saving ? "保存中…" : "保存配置"}</button><button className="ppt-provider-test" type="button" onClick={() => void test()} disabled={testing || !configuredKey}>{testing ? "测试中…" : "测试连接"}</button></div>
      {configuredKey && <button className="ppt-provider-clear" type="button" onClick={() => void clear()}>清除 API Key</button>}
    </div>}
    <small className="ppt-provider-note"><i className="fas fa-lock" aria-hidden="true" /> API Key 将加密保存，仅用于当前教师账号的课件 Agent。</small>
  </aside>;
}

function OutlineBoard({ pages, onSelect, onReorder, onConfirm }: { pages: PptPage[]; onSelect: (page: PptPage) => void; onReorder: (ids: string[]) => void; onConfirm: () => void }) { const [dragId, setDragId] = useState<string | null>(null); const ordered = [...pages].sort((a, b) => a.sort_order - b.sort_order); return <section className="ppt-outline-board"><div className="ppt-board-head"><div><span className="ppt-kicker">OUTLINE BOARD</span><h2>先把教学主线搭稳</h2><p>拖拽页面调整叙事顺序，点击卡片可继续和 Agent 讨论。</p></div><button className="ppt-primary" onClick={onConfirm}>确认大纲，进入生成</button></div><div className="ppt-board-grid">{ordered.map((page, index) => <article key={page.id} draggable onDragStart={() => setDragId(page.id)} onDragOver={(e) => e.preventDefault()} onDrop={() => { if (!dragId || dragId === page.id) return; const ids = ordered.map((item) => item.id); const from = ids.indexOf(dragId); const to = ids.indexOf(page.id); ids.splice(from, 1); ids.splice(to, 0, dragId); onReorder(ids); setDragId(null); }} onClick={() => onSelect(page)} className="ppt-outline-card"><div className="ppt-outline-number">{String(index + 1).padStart(2, "0")}</div><span>{page.section_title || "内容章节"}</span><h3>{page.title}</h3><ul>{page.bullets.slice(0, 4).map((bullet) => <li key={bullet}>{bullet}</li>)}</ul><small>拖拽排序 · 点击编辑</small></article>)}</div></section>; }

function ThemeStep({ themes, selected, onSelect, disabled }: { themes: PptTheme[]; selected?: string | null; onSelect: (id: string) => void; disabled?: boolean }) {
  const [query, setQuery] = useState(""); const [family, setFamily] = useState("all");
  const families = Array.from(new Set(themes.map((t) => t.family))); const visible = themes.filter((t) => (family === "all" || t.family === family) && `${t.name} ${t.description}`.toLowerCase().includes(query.toLowerCase()));
  return <section className="ppt-theme-step"><div className="ppt-board-head"><div><span className="ppt-kicker">CHOOSE THEME</span><h2>选择一套适合课堂的视觉主题</h2><p>选定后，AI 会根据大纲自动完成整套课件的版式与视觉排版。</p></div><span className="ppt-theme-auto-hint">选择主题即开始智能排版</span></div><div className="ppt-theme-toolbar"><input placeholder="搜索主题…" value={query} onChange={(e) => setQuery(e.target.value)} disabled={disabled} /><div>{["all", ...families].map((item) => <button key={item} className={family === item ? "active" : ""} onClick={() => setFamily(item)} disabled={disabled}>{item === "all" ? "全部" : item}</button>)}</div></div><div className="ppt-theme-grid">{visible.map((theme) => <button key={theme.id} disabled={disabled} className={`ppt-theme-card ${selected === theme.id ? "selected" : ""}`} onClick={() => onSelect(theme.id)}><div className="ppt-theme-preview" style={{ background: theme.colors.bg, color: theme.colors.title }}><span style={{ background: theme.colors.accent }} /><b>{theme.name}</b><i style={{ background: theme.colors.accent }} /></div><strong>{theme.name}</strong><small>{theme.description}</small><em>{theme.family} · {theme.layout_count || 0} layouts</em></button>)}</div></section>;
}

function LayoutingStep({ progress, error, onRetry, onChooseTheme }: { progress: number; error?: string | null; onRetry: () => void; onChooseTheme: () => void }) {
  const phases = ["分析大纲结构", "匹配页面版式", "生成视觉设计", "检查排版质量"];
  return <section className="ppt-layout-step ppt-layouting-step"><div className="ppt-layouting-orb">✦</div><span className="ppt-kicker">AI LAYOUT ENGINE</span><h2>{error ? "智能排版没有完成" : "AI 正在为整套课件智能排版"}</h2><p>{error || "正在理解教学节奏、页面角色与内容密度，完成后会自动进入预览编辑。"}</p><div className="ppt-layouting-progress"><div style={{ width: `${progress}%` }} /></div><div className="ppt-layouting-phases">{phases.map((phase, index) => <div key={phase} className={progress >= (index + 1) * 25 ? "done" : progress > index * 25 ? "active" : ""}><span>{progress >= (index + 1) * 25 ? "✓" : String(index + 1).padStart(2, "0")}</span><b>{phase}</b></div>)}</div>{error && <div className="ppt-layouting-actions"><button className="ppt-primary" onClick={onRetry}>重试智能排版</button><button className="ppt-ghost" onClick={onChooseTheme}>返回选择主题</button></div>}</section>;
}

function PreviewEditor({ pages, selected, onSelect, onSave, onReorder, saving }: { pages: PptPage[]; selected: number; onSelect: (index: number) => void; onSave: (page: PptPage, doc: PptDocument) => void; onReorder: (ids: string[]) => void; saving: boolean }) {
  const page = pages[selected]; const fileRef = useRef<HTMLInputElement | null>(null);
  const [dragId, setDragId] = useState<string | null>(null);
  const addImage = async (file: File) => { if (!page) return; const reader = new FileReader(); reader.onload = () => { const doc = editableDocument(page); const next: PptDocument = { ...doc, elements: [...doc.elements, { id: `image-${Date.now()}`, type: "image", x: 58, y: 28, w: 34, h: 42, src: String(reader.result || "") }] }; onSave(page, next); }; reader.readAsDataURL(file); };
  return <div className="ppt-rich-editor"><aside className="ppt-rich-thumbnails"><div className="ppt-thumb-head"><strong>页面</strong><span>{pages.length} 张</span></div><div className="ppt-thumb-list">{pages.map((item, i) => <div key={item.id} draggable onDragStart={() => setDragId(item.id)} onDragOver={(event) => event.preventDefault()} onDrop={() => { if (!dragId || dragId === item.id) return; const ids = pages.map((entry) => entry.id); const from = ids.indexOf(dragId); const to = ids.indexOf(item.id); ids.splice(from, 1); ids.splice(to, 0, dragId); onReorder(ids); setDragId(null); }}><SlideThumbnail page={{ ...item, sort_order: i }} selected={i === selected} onClick={() => onSelect(i)} /></div>)}</div></aside><main className="ppt-rich-main"><div className="ppt-rich-toolbar"><div><span className="ppt-kicker">PREVIEW & EDIT</span><strong>{page?.title}</strong></div><div><button className="ppt-ghost" onClick={() => fileRef.current?.click()}>＋ 添加图片</button><button className="ppt-primary" disabled={saving}>{saving ? "保存中…" : "已自动保存"}</button><input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => { const file = e.target.files?.[0]; if (file) void addImage(file); e.currentTarget.value = ""; }} /></div></div><div className="ppt-rich-canvas"><SlideCanvas page={page} editable onChange={(doc) => page && onSave(page, doc)} /></div><div className="ppt-rich-help">点击文字直接编辑 · 拖动元素调整位置 · 选中元素后可删除 · 支持上传图片并拖拽排版</div></main></div>;
}

export default function CoursewareAgent() {
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId?: string }>();
  const [projects, setProjects] = useState<PptProject[]>([]); const [active, setActive] = useState<PptProject | null>(null); const [pages, setPages] = useState<PptPage[]>([]); const [messages, setMessages] = useState<PptMessage[]>([]); const [requirement, setRequirement] = useState<PptRequirement | null>(null); const [sources, setSources] = useState<PptSource[]>([]); const [themes, setThemes] = useState<PptTheme[]>([]); const [selected, setSelected] = useState(0); const [surface, setSurface] = useState<Surface>("start"); const [loading, setLoading] = useState(false); const [outlineGenerating, setOutlineGenerating] = useState(false); const [layoutProgress, setLayoutProgress] = useState(0); const [layoutError, setLayoutError] = useState<string | null>(null); const [saving, setSaving] = useState(false); const saveTimer = useRef<number | null>(null); const pendingDoc = useRef<{ pageId: string; doc: PptDocument; revision: number } | null>(null); const eventSource = useRef<EventSource | null>(null); const page = pages[selected];
  const [projectLoading, setProjectLoading] = useState(Boolean(projectId)); const [deletingId, setDeletingId] = useState<string | null>(null); const [deleteCandidate, setDeleteCandidate] = useState<PptProject | null>(null); const [removingIds, setRemovingIds] = useState<Record<string, boolean>>({}); const [previewErrors, setPreviewErrors] = useState<Record<string, boolean>>({}); const [previewSources, setPreviewSources] = useState<Record<string, string>>({}); const generationPoll = useRef<number | null>(null); const activeGenerationId = useRef<string | null>(null);
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
  useEffect(() => () => { eventSource.current?.close(); if (saveTimer.current) window.clearTimeout(saveTimer.current); if (generationPoll.current) window.clearInterval(generationPoll.current); }, []);
  useEffect(() => {
    let cancelled = false;
    if (!projectId) {
      setProjectLoading(false); setActive(null); setPages([]); setMessages([]); setRequirement(null); setSources([]); return () => { cancelled = true; };
    }
    setProjectLoading(true); setActive(null);
    pptApi.project(projectId).then(async ({ data }) => {
      if (cancelled) return;
      setSurface(data.page_count ? (data.latest_checkpoint_code ? "outline" : data.theme_id && data.design_status === "ready" ? "editor" : data.theme_id ? "theme" : "theme") : "start");
      await refresh(data);
    }).catch(() => { if (!cancelled) { toast.error("项目不存在或无权访问"); navigate("/teacher/courseware-agent", { replace: true }); } }).finally(() => { if (!cancelled) setProjectLoading(false); });
    return () => { cancelled = true; };
  }, [projectId]);
  const openProject = (project: PptProject) => navigate(`/teacher/courseware-agent/${project.id}`);
  const uploadFiles = async (files: FileList | File[], project = active) => { if (!project) return; setLoading(true); try { for (const file of Array.from(files)) await pptApi.upload(project.id, file); await refresh(project); toast.success("资料已加入当前项目"); } catch (e: any) { toast.error(e.response?.data?.detail || "资料上传失败"); } finally { setLoading(false); } };
  const create = async (text: string, files: File[] = []) => { if (!text.trim()) return; setLoading(true); try { const { data } = await pptApi.createProject({ title: text.trim().slice(0, 32), request_text: text.trim() }); setProjects((items) => [data, ...items]); openProject(data); if (files.length) await uploadFiles(files, data); } catch (e: any) { toast.error(e.response?.data?.detail || "创建项目失败"); } finally { setLoading(false); } };
  const removeProject = async (event: React.MouseEvent, project: PptProject) => { event.stopPropagation(); if (deletingId) return; setDeleteCandidate(project); };
  const confirmRemoveProject = async () => { const project = deleteCandidate; if (!project || deletingId) return; setDeletingId(project.id); try { await pptApi.deleteProject(project.id); setDeleteCandidate(null); setRemovingIds((items) => ({ ...items, [project.id]: true })); window.setTimeout(() => { setProjects((items) => items.filter((item) => item.id !== project.id)); setRemovingIds((items) => { const next = { ...items }; delete next[project.id]; return next; }); }, 420); toast.success("项目已删除"); if (projectId === project.id) navigate("/teacher/courseware-agent", { replace: true }); } catch (e: any) { toast.error(e.response?.data?.detail || "项目删除失败"); } finally { setDeletingId(null); } };
  const generateOutline = async () => { if (!active || !requirement?.ready_to_outline) return; setLoading(true); setOutlineGenerating(true); setSurface("outline"); try { await pptApi.generateOutline(active.id, { page_count_target: active.page_count_target || requirement.page_count_target || 10 }); await refresh(); toast.success("大纲已生成"); } catch (e: any) { toast.error(e.response?.data?.detail || "大纲生成失败"); setSurface("start"); } finally { setOutlineGenerating(false); setLoading(false); } };
  const generateDesign = async () => { if (!active) return; setLoading(true); setLayoutError(null); setLayoutProgress(2); setSurface("layouting"); eventSource.current?.close(); if (generationPoll.current) window.clearInterval(generationPoll.current); activeGenerationId.current = null; const source = new EventSource(pptApi.streamUrl(active.id)); eventSource.current = source; let total = Math.max(1, pages.length); const finish = (ok: boolean, message?: string) => { if (generationPoll.current) { window.clearInterval(generationPoll.current); generationPoll.current = null; } setLoading(false); if (!ok) setLayoutError(message || "智能排版失败，请重试"); source.close(); eventSource.current = null; }; source.onmessage = (event) => { try { const payload = JSON.parse(event.data); const body = payload.payload || {}; if ((payload.event_type === "generation.completed" || payload.event_type === "generation.failed") && !activeGenerationId.current) return; if (activeGenerationId.current && body.job_id && body.job_id !== activeGenerationId.current) return; if (body.total_pages) total = body.total_pages; if (payload.event_type === "page.designed") { setLayoutProgress((current) => Math.max(current, Math.min(96, Math.round(((body.completed_pages || 0) / total) * 100)))); } if (payload.event_type === "planner.completed") setLayoutProgress((current) => Math.max(current, 15)); if (payload.event_type === "generation.completed") { setLayoutProgress(100); void refresh().then(() => { setSelected(0); setSurface("editor"); }); finish(true); toast.success("AI 智能排版完成"); } if (payload.event_type === "generation.failed") finish(false, body.error); } catch { /* ignore malformed event */ } }; source.onerror = () => { /* EventSource retries with Last-Event-ID; polling is the fallback */ }; try { const { data: job } = await pptApi.generateDesign(active.id); activeGenerationId.current = job.id; generationPoll.current = window.setInterval(() => { void pptApi.generationJob(active.id, job.id).then(({ data }) => { total = data.total_pages || total; if (data.total_pages) setLayoutProgress(Math.max(2, Math.min(99, Math.round((data.completed_pages / data.total_pages) * 100)))); if (data.status === "completed" || data.status === "completed_with_errors") { setLayoutProgress(100); void refresh().then(() => { setSelected(0); setSurface("editor"); }); finish(true); } else if (data.status === "failed" || data.status === "cancelled") finish(false, data.error_message || "生成任务已停止"); }).catch(() => undefined); }, 3000); } catch (e: any) { finish(false, e.response?.data?.detail || "智能排版失败，请重试"); setLayoutProgress(0); } };
  const saveDocumentForPage = async (target: PptPage, doc: PptDocument) => {
    pendingDoc.current = { pageId: target.id, doc, revision: target.document_revision || 1 };
    if (saveTimer.current) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(async () => {
      if (!active || !pendingDoc.current) return;
      const payload = pendingDoc.current; pendingDoc.current = null; setSaving(true);
      try { const { data } = await pptApi.patchDocument(active.id, payload.pageId, payload.doc, payload.revision); setPages((items) => items.map((item) => item.id === data.id ? data : item)); }
      catch (e: any) { toast.error(e.response?.data?.detail || "保存画布失败"); await refresh(); }
      finally { setSaving(false); }
    }, 350);
  };
  const flushPendingDocument = async () => {
    if (saveTimer.current) { window.clearTimeout(saveTimer.current); saveTimer.current = null; }
    const payload = pendingDoc.current;
    if (!active || !payload) return;
    pendingDoc.current = null; setSaving(true);
    try {
      const { data } = await pptApi.patchDocument(active.id, payload.pageId, payload.doc, payload.revision);
      setPages((items) => items.map((item) => item.id === data.id ? data : item));
    } catch (e: any) { toast.error(e.response?.data?.detail || "保存画布失败"); await refresh(); }
    finally { setSaving(false); }
  };
  const reorderPages = async (ids: string[]) => {
    if (!active) return;
    const selectedPageId = pages[selected]?.id;
    try {
      const { data } = await pptApi.patchStoryboard(active.id, ids);
      const nextPages = [...data.items].sort((a, b) => a.sort_order - b.sort_order);
      setPages(nextPages);
      const nextSelected = selectedPageId ? nextPages.findIndex((item) => item.id === selectedPageId) : 0;
      setSelected(nextSelected >= 0 ? nextSelected : 0);
    } catch (e: any) { toast.error(e.response?.data?.detail || "页面顺序保存失败"); }
  };
  const confirmOutline = async () => { if (!active) return; try { await pptApi.confirmCheckpoint(active.id, "outline_confirm"); await refresh(); setSurface("theme"); toast.success("大纲已确认，请选择主题"); } catch (e: any) { toast.error(e.response?.data?.detail || "请先生成并确认大纲"); } };
  if (!projectId) return (
    <div className="ppt-immersive-home">
      <div className="ppt-home-layout">
          <div className="ppt-home-main">
            <WelcomeBanner className="ppt-home-agent-banner" eyebrow="课件 AGENT 工作台" title={<>把教学想法，<br /><em>变成一套可用的课件。</em></>} subtitle="告诉 Agent 课程目标、受众和重点，我会和你一起梳理需求、生成大纲，再逐页完善。" />
            <Composer onCreate={create} loading={loading} />
          </div>
          <div className="ppt-recent"><div className="ppt-recent-head"><div><span className="ppt-kicker">PROJECTS</span><h2>最近项目</h2></div><span>{projects.length} 个项目</span></div><div className="ppt-recent-grid">
            {projects.map((project) => <article key={project.id} className={`ppt-recent-card ${removingIds[project.id] ? "is-removing" : ""}`}><button type="button" className="ppt-recent-card-main" onClick={() => openProject(project)}><div className="ppt-mini-preview">{previewSources[project.id] && !previewErrors[project.id] ? <img src={previewSources[project.id]} alt={`${project.title} 首页预览`} onError={() => setPreviewErrors((items) => ({ ...items, [project.id]: true }))} /> : <div className="ppt-mini-fallback"><span>{stageLabels[project.current_stage] || "进行中"}</span><b>{project.page_count || "—"}</b></div>}</div><strong>{project.title}</strong><small>{project.request_text}</small></button><button type="button" className="ppt-project-delete" onClick={(event) => void removeProject(event, project)} disabled={deletingId === project.id} aria-label={`删除项目 ${project.title}`} title="删除项目"><i className="fas fa-trash" /></button></article>)}
            {!projects.length && <div className="ppt-recent-empty">还没有项目，从左侧告诉 Agent 你的教学想法开始。</div>}
          </div></div>
          <ProviderSettings />
      </div>
      <HKUConfirmDialog open={Boolean(deleteCandidate)} scope="surface" eyebrow="DELETE PROJECT" title="删除这个课件项目？" description={deleteCandidate ? <>“{deleteCandidate.title}”中的资料、页面和导出文件都会被删除，且无法恢复。</> : undefined} icon={<i className="fas fa-trash" />} onClose={() => { if (!deletingId) setDeleteCandidate(null); }} onConfirm={confirmRemoveProject} confirmLabel="确认删除" loading={Boolean(deletingId)} labelledBy="ppt-delete-title" />
    </div>
  );
  if (projectLoading || !active) return <div className="ppt-project-loading">正在加载课件项目…</div>;
  return <div className="ppt-immersive-shell">
    <ProjectSidebar active={active} surface={surface} pages={pages} selected={selected} onSurface={setSurface} onSelectPage={(index) => { setSelected(index); setSurface("editor"); }} />
    <div className="ppt-immersive-body">
      <header className="ppt-immersive-header"><div className="ppt-project-title"><span className="ppt-kicker">PPT STUDIO · WORKSPACE</span><strong>{active.title}</strong></div><div className="ppt-header-actions"><div className="ppt-stage-line">{["init", "outline", "theme", "layout", "design", "export"].map((stage) => <span key={stage} className={active.current_stage === stage || (["theme", "layout"].includes(stage) && !!active.theme_id) || (stage === "design" && pages.some((p) => !!p.document)) ? "active" : ""}>{stageLabels[stage]}</span>)}</div>{pages.length > 0 && <button onClick={() => setSurface("present")} className="ppt-ghost">放映</button>}<button className="ppt-primary" disabled={!pages.some((p) => !!p.document)} onClick={async () => { try { const { data } = await pptApi.export(active.id); toast.success("已开始生成 PPT 文件"); const poll = window.setInterval(async () => { try { const status = await pptApi.exportStatus(active.id, data.id); if (status.data.status === "completed") { window.clearInterval(poll); const response = await pptApi.downloadExport(active.id, data.id); const url = URL.createObjectURL(response.data); const link = document.createElement("a"); link.href = url; link.download = "courseware.pptx"; document.body.appendChild(link); link.click(); link.remove(); window.setTimeout(() => URL.revokeObjectURL(url), 1000); } else if (status.data.status === "failed") { window.clearInterval(poll); toast.error(status.data.error || "导出失败"); } } catch { /* keep polling */ } }, 1200); } catch (e: any) { toast.error(e.response?.data?.detail || "导出失败"); } }}>导出 PPT</button></div></header>
      {surface === "start" && <div className="ppt-start-grid"><Chat project={active} messages={messages.filter((m) => !m.page_id)} requirement={requirement} sources={sources} onRequirementUpdate={(response) => setRequirement((current) => ({ ...(current || {}), ...response }))} onUpload={(files) => void uploadFiles(files)} onSent={() => void refreshMessages()} /><section className={`ppt-start-brief ${requirement?.brief_summary ? "is-ready" : ""}`}><span className="ppt-kicker">PROJECT BRIEF</span><h2>{requirement?.brief_summary ? "你的课件需求摘要" : "我们先把问题说清楚"}</h2><p>{requirement?.brief_summary || active.request_text}</p><div className="ppt-brief-points"><div><b>01</b><span>{requirement?.answers?.audience || "受众待确认"}</span></div><div><b>02</b><span>{requirement?.answers?.goals || "教学目标待确认"}</span></div><div><b>03</b><span>{requirement?.answers?.duration || requirement?.answers?.slide_count || "课堂节奏待确认"}</span></div></div>{requirement?.suggested_additions?.length ? <p className="ppt-extra-hint">还可以补充：{requirement.suggested_additions.join("、")}</p> : null}<button className="ppt-primary wide" onClick={() => void generateOutline()} disabled={loading || !requirement?.ready_to_outline}>{loading ? "正在生成大纲…" : requirement?.ready_to_outline ? "生成我的大纲 →" : "完成需求对话后生成大纲"}</button></section></div>}
      {surface === "outline" && <div className="ppt-workspace-grid">{outlineGenerating ? <section className="ppt-outline-generating"><div className="ppt-layouting-orb">✦</div><span className="ppt-kicker">OUTLINE ENGINE</span><h2>正在把对话整理成教学主线</h2><p>正在提炼章节、页面职责与课堂节奏…</p><div className="ppt-outline-loading-bar"><i /></div></section> : <OutlineBoard pages={pages} onSelect={(item) => { setSelected(pages.findIndex((p) => p.id === item.id)); }} onReorder={(ids) => { void pptApi.patchStoryboard(active.id, ids).then(() => refresh()); }} onConfirm={() => void confirmOutline()} />}<Chat project={active} page={page} messages={messages.filter((m) => !m.page_id || m.page_id === page?.id)} onSent={() => void refresh()} /></div>}
      {surface === "theme" && <ThemeStep themes={themes} selected={active.theme_id} onSelect={async (themeId) => { if (loading) return; try { const { data } = await pptApi.selectTheme(active.id, themeId); setActive(data); await generateDesign(); } catch (e: any) { setLayoutError(e.response?.data?.detail || "主题保存失败"); setSurface("layouting"); } }} disabled={loading} />}
      {surface === "layouting" && <LayoutingStep progress={layoutProgress} error={layoutError} onRetry={() => void generateDesign()} onChooseTheme={() => { setLayoutError(null); setSurface("theme"); }} />}
      {surface === "editor" && page && <div className="ppt-editor-grid"><main className="ppt-editor-main"><PreviewEditor pages={pages} selected={selected} onSelect={setSelected} onReorder={(ids) => void reorderPages(ids)} onSave={(target, doc) => void saveDocumentForPage(target, doc)} saving={saving} /></main><aside className="ppt-editor-side"><div className="ppt-side-tabs"><button className="active">对话</button><button>属性</button></div><Chat project={active} page={page} messages={messages.filter((m) => m.page_id === page.id)} onBeforeAgent={flushPendingDocument} onAgentSlideFocus={setSelected} onSent={() => refresh()} /><div className="ppt-element-hint"><span className="ppt-kicker">EDIT MODE</span><p>点击文字直接编辑，拖拽元素调整位置；选中元素后可删除。预览与导出使用同一份渲染结果。</p></div></aside></div>}
      {surface === "present" && pages.length > 0 && <Presentation pages={pages} index={selected} onIndexChange={setSelected} onClose={() => setSurface("editor")} />}
    </div>
  </div>;
}

function ProjectSidebar({ active, surface, pages, selected, onSurface, onSelectPage }: { active: PptProject; surface: Surface; pages: PptPage[]; selected: number; onSurface: (surface: Surface) => void; onSelectPage: (index: number) => void }) {
  return <aside className="ppt-project-sidebar"><div className="ppt-sidebar-brand"><span>HKU</span><div><b>课件 Studio</b><small>PROJECT WORKSPACE</small></div></div><div className="ppt-sidebar-project"><span className="ppt-kicker">当前项目</span><strong>{active.title}</strong><small>{active.page_count || 0} 页 · {stageLabels[active.current_stage] || "进行中"}</small></div><nav className="ppt-project-nav"><button className={surface === "start" ? "active" : ""} onClick={() => onSurface("start")}>✦ 对话与需求</button><button className={surface === "outline" ? "active" : ""} onClick={() => onSurface("outline")} disabled={!pages.length}>▦ 故事板大纲</button><button className={surface === "theme" ? "active" : ""} onClick={() => onSurface("theme")} disabled={!pages.length}>◉ 选择主题</button><button className={surface === "editor" ? "active" : ""} onClick={() => onSurface("editor")} disabled={!pages.some((item) => !!item.document)}>◈ 预览编辑</button></nav>{pages.length > 0 && surface !== "editor" && <div className="ppt-sidebar-pages"><div><span>页面</span><small>{pages.length} 张</small></div>{pages.map((item, index) => <button key={item.id} className={selected === index ? "active" : ""} onClick={() => onSelectPage(index)}><span>{String(index + 1).padStart(2, "0")}</span><b>{item.title || "未命名页面"}</b></button>)}</div>}<div className="ppt-sidebar-footer">对话驱动 · 所见即所得</div></aside>;
}

function Composer({ onCreate, loading }: { onCreate: (text: string, files: File[]) => void; loading: boolean }) { const [text, setText] = useState(""); const [files, setFiles] = useState<File[]>([]); return <div className="ppt-home-composer"><textarea value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onCreate(text, files); } }} placeholder="告诉 Agent 你想讲什么，例如：为大一学生设计一节 50 分钟的可持续设计课程" rows={3} /><div className={`ppt-home-files ${files.length ? "has-files" : ""}`}>{files.length ? files.map((file) => <span key={`${file.name}-${file.lastModified}`}>📎 {file.name}<button type="button" onClick={() => setFiles((items) => items.filter((item) => item !== file))}>×</button></span>) : <span className="ppt-home-files-placeholder"><i className="fas fa-paperclip" /> 可添加 PDF、Markdown 或图片作为 Agent 的参考资料</span>}</div><div><label className="ppt-upload-button">＋ 添加资料<input type="file" multiple accept=".pdf,.md,.markdown,image/png,image/jpeg,image/webp" onChange={(e) => setFiles((items) => [...items, ...Array.from(e.target.files || [])])} /></label><small>Enter 发送 · Shift + Enter 换行</small><button onClick={() => onCreate(text, files)} disabled={loading || !text.trim()}>{loading ? "创建中…" : "开始创建 →"}</button></div></div>; }
function Presentation({ pages, index, onIndexChange, onClose }: { pages: PptPage[]; index: number; onIndexChange: (index: number) => void; onClose: () => void }) {
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
    <button className="ppt-presentation-close" onClick={onClose} aria-label="退出放映">×</button>
    <div className="ppt-presentation-title"><span>放映预览</span><strong>{page.title}</strong></div>
    <div className="ppt-presentation-stage" ref={stageRef}>
      <button aria-label="上一页" disabled={index === 0} onClick={() => onIndexChange(Math.max(0, index - 1))}>‹</button>
      <div className="ppt-rendered-slide" style={{ width: slideWidth, height: slideHeight }}>
        <div className="ppt-present-scale" style={{ width: SLIDE_WIDTH, height: SLIDE_HEIGHT, transform: `scale(${scale})` }}><SlideRenderer document={editableDocument(page)} /></div>
      </div>
      <button aria-label="下一页" disabled={index === pages.length - 1} onClick={() => onIndexChange(Math.min(pages.length - 1, index + 1))}>›</button>
    </div>
    <div className="ppt-presentation-footer">{index + 1} / {pages.length}<span>← → 切换 · Esc 退出</span></div>
  </div>;
}
