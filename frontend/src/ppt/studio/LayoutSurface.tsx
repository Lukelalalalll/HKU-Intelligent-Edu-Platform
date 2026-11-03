/**
 * Layout surface: calm progress feedback for the design generation job.
 */
import React from "react";
import { useI18n, type TranslationKey } from "../../i18n";
import { StudioIcon } from "./icons";
import type { StudioModel } from "./types";

export type LayoutSurfaceProps = { model: StudioModel };

const PHASES: TranslationKey[] = [
  "coursewareAgent.layouting.phases.analyse",
  "coursewareAgent.layouting.phases.match",
  "coursewareAgent.layouting.phases.design",
  "coursewareAgent.layouting.phases.check",
];
const THRESHOLDS = [8, 32, 68, 94];

/** Full-screen generation progress. */
export default function LayoutSurface({ model }: LayoutSurfaceProps) {
  const { t } = useI18n();
  const { layout, actions } = model;
  const progress = Math.max(0, Math.min(100, layout.progress || 0));
  const circumference = 2 * Math.PI * 46;

  return (
    <div className="st-surface st-layouting" data-testid="studio-surface-layouting">
      <div className="st-layouting-card">
        {layout.error ? (
          <>
            <span className="st-layouting-mark is-error" aria-hidden="true"><StudioIcon name="alert" size={22} /></span>
            <span className="st-eyebrow">{t("coursewareAgent.workspace.steps.theme")} · {t("coursewareAgent.stages.layout")}</span>
            <h2>{t("coursewareAgent.layouting.failedTitle")}</h2>
            <p className="st-layouting-error">{layout.error}</p>
            <div className="st-layouting-actions">
              <button type="button" className="st-primary-button" onClick={actions.retryDesign}>
                <StudioIcon name="refresh" size={14} /> {t("coursewareAgent.layouting.retry")}
              </button>
              <button type="button" className="st-ghost-button" onClick={() => actions.navigate("theme")}>
                <StudioIcon name="back" size={14} /> {t("coursewareAgent.layouting.backToTheme")}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="st-ring" role="status" aria-live="polite" aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress}>
              <svg viewBox="0 0 108 108" aria-hidden="true">
                <circle className="st-ring-track" cx="54" cy="54" r="46" />
                <circle className="st-ring-value" cx="54" cy="54" r="46" strokeDasharray={circumference} strokeDashoffset={circumference * (1 - progress / 100)} />
              </svg>
              <span>{progress}%</span>
            </div>
            <span className="st-eyebrow">{t("coursewareAgent.workspace.steps.theme")} · {t("coursewareAgent.stages.layout")}</span>
            <h2>{progress >= 100 ? t("coursewareAgent.layouting.ready") : t("coursewareAgent.layouting.title")}</h2>
            <p>{t("coursewareAgent.layouting.subtitle")}</p>
            <ol className="st-layouting-phases">
              {PHASES.map((phase, index) => {
                const threshold = THRESHOLDS[index];
                const done = progress >= threshold;
                const active = !done && progress >= (THRESHOLDS[index - 1] ?? 0);
                return (
                  <li key={phase} className={done ? "is-done" : active ? "is-active" : ""}>
                    <span className="st-layouting-step" aria-hidden="true">
                      {done ? <StudioIcon name="check" size={12} /> : active ? <i className="st-spinner" /> : String(index + 1).padStart(2, "0")}
                    </span>
                    <b>{t(phase)}</b>
                  </li>
                );
              })}
            </ol>
            <button type="button" className="st-ghost-button st-layouting-back" onClick={() => actions.navigate("theme")}>
              <StudioIcon name="back" size={14} /> {t("coursewareAgent.layouting.backToTheme")}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
