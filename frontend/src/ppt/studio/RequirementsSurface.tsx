/**
 * Requirements surface: the interview on the left, the living brief on the right.
 */
import React from "react";
import { useI18n } from "../../i18n";
import ChatPanel from "./ChatPanel";
import { StudioIcon } from "./icons";
import type { StudioModel } from "./types";

export type RequirementsSurfaceProps = { model: StudioModel };

/** First step of the studio flow. */
export default function RequirementsSurface({ model }: RequirementsSurfaceProps) {
  const { t } = useI18n();
  const { project, messages, requirement, sources, outlineGenerating, actions } = model;
  const answers = requirement?.answers || {};
  const ready = Boolean(requirement?.ready_to_outline);
  const additions = requirement?.suggested_additions || [];
  const text = (value: unknown) => (value == null || value === "" ? "" : String(value));
  const pacingParts = [text(answers.duration), project.page_count_target ? t(project.page_count_target === 1 ? "coursewareAgent.home.pagesCount.one" : "coursewareAgent.home.pagesCount.other", { count: project.page_count_target }) : ""].filter(Boolean);
  const briefRows = [
    { index: "01", label: t("coursewareAgent.requirements.audience"), value: text(answers.audience) },
    { index: "02", label: t("coursewareAgent.requirements.goals"), value: text(answers.goals) },
    { index: "03", label: t("coursewareAgent.requirements.pacing"), value: pacingParts.join(" · ") },
  ];

  return (
    <div className="st-surface st-requirements" data-testid="studio-surface-requirements">
      <header className="st-surface-head">
        <div>
          <span className="st-eyebrow">01 · {t("coursewareAgent.workspace.steps.requirements")}</span>
          <h2>{t("coursewareAgent.requirements.title")}</h2>
          <p>{t("coursewareAgent.requirements.subtitle")}</p>
        </div>
        <span className={`st-state-pill ${ready ? "is-ready" : ""}`}>
          <i aria-hidden="true" /> {ready ? t("coursewareAgent.requirements.ready") : t("coursewareAgent.requirements.notReady")}
        </span>
      </header>

      <div className="st-surface-body st-requirements-body">
        <section className="st-card st-chat-card">
          <header className="st-card-head">
            <div>
              <strong>{t("coursewareAgent.requirements.conversationTitle")}</strong>
              <small>{t("coursewareAgent.requirements.conversationHint")}</small>
            </div>
            <span className="st-mark" aria-hidden="true"><StudioIcon name="sparkle" size={14} /></span>
          </header>
          <ChatPanel
            project={project}
            page={undefined}
            messages={messages.filter((message) => !message.page_id)}
            requirement={requirement}
            sources={sources}
            onSent={actions.refreshMessages}
            onUpload={actions.uploadFiles}
            onRequirementUpdate={actions.updateRequirement}
            className="st-chat-card-inner"
          />
        </section>

        <aside className="st-card st-brief">
          <header className="st-brief-head">
            <span className="st-eyebrow">BRIEF</span>
            <h3>{t("coursewareAgent.requirements.briefTitle")}</h3>
          </header>
          <p className={`st-brief-summary ${requirement?.brief_summary ? "" : "is-empty"}`}>
            {requirement?.brief_summary || t("coursewareAgent.requirements.briefEmpty")}
          </p>
          <dl className="st-brief-list">
            {briefRows.map((row) => (
              <div key={row.index} className={row.value ? "" : "is-pending"}>
                <dt><b>{row.index}</b><span>{row.label}</span></dt>
                <dd>{row.value || t("coursewareAgent.requirements.pending")}</dd>
              </div>
            ))}
          </dl>
          {additions.length ? (
            <div className="st-brief-additions">
              <span>{t("coursewareAgent.requirements.additions")}</span>
              <ul>{additions.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>
          ) : null}
          <div className={`st-readiness ${ready ? "is-ready" : ""}`}>
            <span aria-hidden="true"><StudioIcon name={ready ? "check" : "alert"} size={13} /></span>
            {ready ? t("coursewareAgent.requirements.ready") : t("coursewareAgent.requirements.notReady")}
          </div>
          <small className="st-brief-hint">{t("coursewareAgent.requirements.generateHint")}</small>
        </aside>
      </div>

      <footer className="st-surface-foot">
        <span className="st-foot-hint">{t("coursewareAgent.requirements.generateHint")}</span>
        <div className="st-foot-actions">
          <button type="button" className="st-primary-button" onClick={actions.generateOutline} disabled={!ready || outlineGenerating}>
            {outlineGenerating ? t("coursewareAgent.requirements.generating") : t("coursewareAgent.requirements.generate")}
            <StudioIcon name="next" size={15} />
          </button>
        </div>
      </footer>
    </div>
  );
}
