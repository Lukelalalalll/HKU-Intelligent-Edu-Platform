/**
 * Streaming conversation panel shared by the interview and refinement modes.
 */
import React, { useEffect, useRef, useState } from "react";
import type { LessonPlanMessage, LessonPlanQuestion } from "../../api";
import { useI18n } from "../../i18n";
import { Markdown } from "../../shared/components/Markdown";
import { LESSON_PLAN_ACCEPT } from "./lessonPlanFormat";

export type LessonPlanChatProps = {
  messages: LessonPlanMessage[];
  question: LessonPlanQuestion | null;
  busy: boolean;
  streamText: string;
  statusText: string;
  error: string | null;
  pendingText: string | null;
  hasPages: boolean;
  disabled?: boolean;
  onSend: (content: string, optionLabel?: string) => void;
  onRetry: () => void;
  onUpload: (files: FileList | File[]) => void;
};

/** Conversation surface for the lesson plan workspace. */
export default function LessonPlanChat({ messages, question, busy, streamText, statusText, error, pendingText, hasPages, disabled = false, onSend, onRetry, onUpload }: LessonPlanChatProps) {
  const { t } = useI18n();
  const [value, setValue] = useState("");
  const streamRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const hasConversation = Boolean(messages.length || pendingText || busy);

  useEffect(() => {
    const node = streamRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, streamText, pendingText, busy]);

  useEffect(() => {
    const node = inputRef.current;
    if (!node) return;
    node.style.height = "auto";
    node.style.height = `${Math.min(150, Math.max(44, node.scrollHeight))}px`;
  }, [value]);

  const send = (content = value.trim(), optionLabel?: string) => {
    if (disabled || busy || (!content && !optionLabel)) return;
    setValue("");
    onSend(content, optionLabel);
  };

  const retry = () => {
    if (!error) return;
    onRetry();
  };

  return (
    <section className="lesson-chat" aria-label={t("lessonPlan.chat.agentLabel")}>
      <div className="lesson-chat-stream" ref={streamRef} aria-live="polite">
        {hasConversation ? (
          <>
            {messages.map((message) => (
              <div key={message.id} className={`lesson-message ${message.role === "user" ? "is-user" : "is-agent"}`}>
                <span className="lesson-message-meta">{message.role === "user" ? t("lessonPlan.chat.youLabel") : t("lessonPlan.chat.agentLabel")}</span>
                <div className="lesson-message-bubble">
                  {message.role === "assistant" ? <Markdown text={message.content_md} /> : <p>{message.content_md}</p>}
                </div>
              </div>
            ))}
            {pendingText ? (
              <div className="lesson-message is-user is-pending">
                <span className="lesson-message-meta">{t("lessonPlan.chat.youLabel")}</span>
                <div className="lesson-message-bubble"><p>{pendingText}</p></div>
              </div>
            ) : null}
            {busy ? (
              <div className="lesson-message is-agent is-live">
                <span className="lesson-message-meta">{t("lessonPlan.chat.agentLabel")}</span>
                <div className="lesson-message-bubble">
                  {streamText ? <Markdown text={streamText} /> : (
                    <p className="lesson-thinking">
                      {statusText || t("lessonPlan.chat.thinking")}
                      <i aria-hidden="true" /><i aria-hidden="true" /><i aria-hidden="true" />
                    </p>
                  )}
                </div>
              </div>
            ) : null}
          </>
        ) : (
          <div className="lesson-chat-empty">
            <div className="lesson-spark" aria-hidden="true">✦</div>
            <h3>{hasPages ? t("lessonPlan.chat.welcomeRefineTitle") : t("lessonPlan.chat.welcomeTitle")}</h3>
            <p>{hasPages ? t("lessonPlan.chat.welcomeRefineBody") : t("lessonPlan.chat.welcomeBody")}</p>
          </div>
        )}

        {error ? (
          <div className="lesson-chat-error" role="alert">
            <span>{error}</span>
            <button type="button" onClick={retry}>{t("lessonPlan.chat.retry")}</button>
          </div>
        ) : null}

        {!busy && question?.options.length ? (
          <div className="lesson-chat-options">
            {question.options.map((option) => (
              <button type="button" key={option} onClick={() => send("", option)} disabled={disabled}>{option}</button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="lesson-chat-composer">
        <textarea
          ref={inputRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            const composing = event.nativeEvent.isComposing || event.keyCode === 229;
            if (event.key === "Enter" && !event.shiftKey && !composing) {
              event.preventDefault();
              send();
            }
          }}
          placeholder={hasPages ? t("lessonPlan.chat.placeholderRefine") : t("lessonPlan.chat.placeholder")}
          rows={1}
          disabled={disabled || busy}
          aria-label={hasPages ? t("lessonPlan.chat.placeholderRefine") : t("lessonPlan.chat.placeholder")}
        />
        <div className="lesson-chat-tools">
          <label className="lesson-attach">
            <input
              type="file"
              multiple
              accept={LESSON_PLAN_ACCEPT}
              disabled={disabled || busy}
              onChange={(event) => { onUpload(event.target.files || []); event.currentTarget.value = ""; }}
            />
            <span>+</span> {t("lessonPlan.chat.addMaterial")}
          </label>
          <span className="lesson-chat-hint">{t("lessonPlan.chat.enterHint")}</span>
          <button type="button" className="lesson-send" onClick={() => send()} disabled={disabled || busy || !value.trim()} aria-label={t("lessonPlan.chat.send")}>
            ↑
          </button>
        </div>
      </div>
    </section>
  );
}
