/**
 * Studio chat panel: requirements interview, outline discussion and the page
 * Agent share this component.
 *
 * All request state lives here; callers only provide the conversation data and
 * a refresh callback.
 */
import React, { useEffect, useRef, useState } from "react";
import type { PptChatStreamEvent, PptMessage, PptPage, PptProject, PptRequirement, PptSource, RequirementChatResponse } from "../../api";
import { pptApi } from "../../api";
import { useI18n } from "../../i18n";
import { StudioIcon } from "./icons";
import Markdown from "./markdown";

export type ChatPanelProps = {
  project: PptProject;
  /** When present the panel talks to the page Agent instead of the requirement interview. */
  page?: PptPage;
  messages: PptMessage[];
  requirement: PptRequirement | null;
  sources?: PptSource[];
  onSent: () => void | Promise<unknown>;
  onUpload?: (files: FileList) => void;
  onBeforeAgent?: () => Promise<void>;
  onAgentSlideFocus?: (index: number) => void;
  onRequirementUpdate?: (response: RequirementChatResponse) => void;
  /** Header slot rendered above the stream. */
  header?: React.ReactNode;
  className?: string;
};

/** Pending message shown before the server echo arrives. */
type Pending = { text: string; option?: string };

export default function ChatPanel({ project, page, messages, requirement, sources = [], onSent, onUpload, onBeforeAgent, onAgentSlideFocus, onRequirementUpdate, header, className = "" }: ChatPanelProps) {
  const { t } = useI18n();
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [activities, setActivities] = useState<PptChatStreamEvent[]>([]);
  const [optimistic, setOptimistic] = useState<PptMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const lastAssistant = [...messages].reverse().find((item) => item.role === "assistant");
  const question = !page ? (lastAssistant?.payload?.question || requirement?.questions?.[0]) : null;
  const hasConversation = Boolean(messages.length || optimistic || sending);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    const node = streamRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, streamText, optimistic, sending]);

  useEffect(() => {
    const node = inputRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(168, Math.max(46, node.scrollHeight))}px`;
  }, [value]);

  const send = async (content = value.trim(), option?: string) => {
    if ((!content && !option) || sending) return;
    const text = content || option || "";
    setSending(true); setValue(""); setStreamText(""); setActivities([]); setError(null); setPending({ text, option });
    setOptimistic({
      id: `optimistic-${Date.now()}`,
      role: "user",
      stage: page ? "editor" : "init",
      scope_type: page ? "page" : "project",
      page_id: page?.id,
      content_md: text,
      payload: {},
      created_at: new Date().toISOString(),
    });
    if (!page) {
      const controller = new AbortController();
      abortRef.current = controller;
      try {
        const complete = await pptApi.streamRequirementChat(project.id, { content: text, option_id: option, option_label: option }, {
          onEvent: (event: PptChatStreamEvent) => {
            if (event.type === "chunk") setStreamText((current) => current + (event.chunk || ""));
            if (event.type === "complete" && event.requirement) onRequirementUpdate?.(event.requirement);
          },
        }, controller.signal);
        if (complete?.requirement) onRequirementUpdate?.(complete.requirement);
        await onSent();
        setPending(null);
      } catch (requestError: any) {
        if (requestError?.name !== "AbortError") setError(requestError?.response?.data?.detail || requestError?.message || t("coursewareAgent.chat.sendFailed"));
      } finally {
        abortRef.current = null; setSending(false); setOptimistic(null); setStreamText(""); setActivities([]);
      }
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await onBeforeAgent?.();
      await pptApi.streamMessage(project.id, { content: text, page_id: page.id, ui_surface: "editor" }, {
        onEvent: (event: PptChatStreamEvent) => {
          if (event.type === "chunk") setStreamText((current) => current + (event.chunk || ""));
          if (event.type === "trace") {
            setActivities((current) => [...current, event]);
            const target = event.trace?.slideIndex;
            if (typeof target === "number" && target >= 0) onAgentSlideFocus?.(target);
          }
        },
      }, controller.signal);
      await onSent();
      setPending(null);
    } catch (requestError: any) {
      if (requestError?.name !== "AbortError") setError(requestError?.response?.data?.detail || requestError?.message || t("coursewareAgent.chat.sendFailed"));
    } finally {
      abortRef.current = null; setSending(false); setOptimistic(null); setStreamText(""); setActivities([]);
    }
  };

  const stop = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setSending(false);
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    const composing = event.nativeEvent.isComposing || event.keyCode === 229;
    if (event.key === "Enter" && !event.shiftKey && !composing) {
      event.preventDefault();
      void send();
    }
  };

  const upload = (files: FileList | null) => {
    if (!files?.length || !onUpload) return;
    onUpload(files);
  };

  return (
    <section className={`st-chat ${className}`.trim()}>
      {header}
      <div className="st-chat-stream" ref={streamRef} aria-live="polite">
        {hasConversation ? (
          <>
            {messages.map((message) => (
              <div key={message.id} className={`st-chat-message ${message.role === "user" ? "is-user" : "is-agent"}`}>
                {message.role === "assistant" ? <span className="st-chat-avatar" aria-hidden="true"><StudioIcon name="sparkle" size={13} /></span> : null}
                <div className="st-chat-body">
                  <span className="st-chat-meta">{message.role === "user" ? t("coursewareAgent.chat.youLabel") : t("coursewareAgent.chat.agentLabel")}</span>
                  <div className="st-chat-bubble">
                    {message.role === "assistant" ? <Markdown text={message.content_md} /> : <p>{message.content_md}</p>}
                  </div>
                  {message.payload?.action_type ? <small className="st-chat-note">{t("coursewareAgent.chat.executed", { action: message.payload.action_type })}</small> : null}
                </div>
              </div>
            ))}
            {optimistic ? (
              <div className="st-chat-message is-user is-pending">
                <div className="st-chat-body">
                  <span className="st-chat-meta">{t("coursewareAgent.chat.youLabel")}</span>
                  <div className="st-chat-bubble"><p>{optimistic.content_md}</p></div>
                  <small className="st-chat-note">{t("coursewareAgent.chat.sending")}</small>
                </div>
              </div>
            ) : null}
            {sending ? (
              <div className="st-chat-message is-agent is-live">
                <span className="st-chat-avatar" aria-hidden="true"><StudioIcon name="sparkle" size={13} /></span>
                <div className="st-chat-body">
                  <span className="st-chat-meta">{t("coursewareAgent.chat.agentLabel")}</span>
                  <div className="st-chat-bubble">
                    {streamText ? <Markdown text={streamText} /> : <p className="st-chat-thinking">{t("coursewareAgent.chat.thinking")}<i /><i /><i /></p>}
                  </div>
                  {activities.length ? (
                    <details className="st-chat-traces">
                      <summary>{t("coursewareAgent.chat.steps", { count: activities.length })}</summary>
                      <ul>
                        {activities.map((event, index) => (
                          <li key={`${event.trace?.tool}-${index}`}>{event.trace?.status === "success" ? "✓" : event.trace?.status === "error" ? "!" : "⋯"} {event.trace?.message || event.status}</li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </div>
              </div>
            ) : null}
          </>
        ) : (
          <div className="st-chat-empty">
            <span className="st-chat-empty-mark" aria-hidden="true"><StudioIcon name="sparkle" size={22} /></span>
            <h3>{t(page ? "coursewareAgent.chat.emptyTitlePage" : "coursewareAgent.chat.emptyTitle")}</h3>
            <p>{t(page ? "coursewareAgent.chat.emptyBodyPage" : "coursewareAgent.chat.emptyBody")}</p>
          </div>
        )}
        {error ? (
          <div className="st-chat-error" role="alert">
            <span>{error}</span>
            <button type="button" onClick={() => { if (pending) void send(pending.text, pending.option); }}>{t("coursewareAgent.chat.retry")}</button>
          </div>
        ) : null}
        {!page && question?.options?.length ? (
          <div className="st-chat-options">
            {question.options.map((option: string) => (
              <button key={option} type="button" onClick={() => void send("", option)} disabled={sending}>{option}</button>
            ))}
          </div>
        ) : null}
        {!page && sources.length ? (
          <div className="st-chat-sources">
            {sources.map((source) => (
              <span key={source.id}><StudioIcon name="file" size={13} /> {source.title}</span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="st-chat-composer">
        <textarea
          ref={inputRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={page ? t("coursewareAgent.chat.placeholderPage") : t("coursewareAgent.chat.placeholderProject")}
          rows={1}
          disabled={sending}
          aria-label={page ? t("coursewareAgent.chat.placeholderPage") : t("coursewareAgent.chat.placeholderProject")}
        />
        <div className="st-chat-tools">
          {onUpload ? (
            <label className="st-chat-attach">
              <StudioIcon name="attach" size={15} />
              <span>{t("coursewareAgent.chat.addMaterials")}</span>
              <input
                type="file"
                multiple
                accept=".pdf,.pptx,.docx,.xlsx,.xls,.txt,.md,.markdown,.csv,.json,image/png,image/jpeg,image/webp"
                onChange={(event) => { upload(event.target.files); event.currentTarget.value = ""; }}
              />
            </label>
          ) : <span />}
          {sending ? (
            <button type="button" className="st-chat-send is-stop" onClick={stop} aria-label={t("coursewareAgent.chat.stop")} title={t("coursewareAgent.chat.stop")}>
              <StudioIcon name="stop" size={14} />
            </button>
          ) : (
            <button type="button" className="st-chat-send" onClick={() => void send()} disabled={!value.trim()} aria-label={t("coursewareAgent.chat.send")} title={t("coursewareAgent.chat.send")}>
              <StudioIcon name="send" size={15} />
            </button>
          )}
        </div>
        <small className="st-chat-hint">{t("coursewareAgent.chat.composerHint")}</small>
      </div>
    </section>
  );
}
