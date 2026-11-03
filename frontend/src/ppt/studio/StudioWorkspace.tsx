/**
 * Workspace frame: one top bar, one stepper and the active surface.
 */
import React from "react";
import { useI18n, type TranslationKey } from "../../i18n";
import type { StepSurface } from "./types";
import type { StudioModel } from "./types";
import { STEP_ORDER, canOpenStep, stageKey, stepStates } from "./stages";
import { StudioIcon, type StudioIconName } from "./icons";
import RequirementsSurface from "./RequirementsSurface";
import OutlineSurface from "./OutlineSurface";
import VisualSurface from "./VisualSurface";
import ThemeSurface from "./ThemeSurface";
import LayoutSurface from "./LayoutSurface";
import EditorSurface from "./EditorSurface";
import PresentSurface from "./PresentSurface";

const stepMeta: Record<StepSurface, { icon: StudioIconName; label: TranslationKey }> = {
  start: { icon: "message", label: "coursewareAgent.workspace.steps.requirements" },
  outline: { icon: "pages", label: "coursewareAgent.workspace.steps.storyboard" },
  visual: { icon: "image", label: "coursewareAgent.workspace.steps.visuals" },
  theme: { icon: "palette", label: "coursewareAgent.workspace.steps.theme" },
  editor: { icon: "layout", label: "coursewareAgent.workspace.steps.edit" },
};

export type StudioWorkspaceProps = { model: StudioModel };

/** Render the workspace chrome around the active surface. */
export default function StudioWorkspace({ model }: StudioWorkspaceProps) {
  const { t } = useI18n();
  const { project, pages, surface, layout, visualRunning, exportState, actions } = model;
  const activeStep: StepSurface = surface === "layouting" ? "theme" : surface === "present" ? "editor" : surface;
  const states = stepStates(project, pages, activeStep);
  const hasDocuments = pages.some((page) => Boolean(page.document));
  const exporting = exportState === "exporting";
  const progress = layout.running ? layout.progress : null;

  const surfaceContent = () => {
    switch (surface) {
      case "outline": return <OutlineSurface model={model} />;
      case "visual": return <VisualSurface model={model} />;
      case "theme": return <ThemeSurface model={model} />;
      case "layouting": return <LayoutSurface model={model} />;
      case "editor": return <EditorSurface model={model} />;
      case "present": return <PresentSurface pages={pages} index={model.selected} onIndexChange={actions.selectPage} onClose={() => actions.navigate("editor")} />;
      default: return <RequirementsSurface model={model} />;
    }
  };

  return (
    <div className="st-workspace" data-testid="studio-workspace">
      <header className="st-topbar">
        <div className="st-topbar-left">
          <button type="button" className="st-back" onClick={actions.goHome} title={t("coursewareAgent.workspace.allDecks")}>
            <StudioIcon name="back" size={16} />
            <span>{t("coursewareAgent.workspace.allDecks")}</span>
          </button>
          <div className="st-project">
            <strong className="st-project-title" title={project.title}>{project.title}</strong>
            <span className="st-project-meta">
              {surface === "editor" && pages.length
                ? t("coursewareAgent.editor.pageOf", { current: model.selected + 1, total: pages.length })
                : t(stageKey(project.current_stage))}
            </span>
          </div>
        </div>

        <nav className="st-steps" aria-label={t("coursewareAgent.workspace.navigation")}>
          {STEP_ORDER.map((step) => {
            const state = states[step];
            const meta = stepMeta[step];
            const disabled = !canOpenStep(state);
            return (
              <button
                key={step}
                type="button"
                className={`st-step is-${state}`}
                onClick={() => { if (!disabled) actions.navigate(step); }}
                disabled={disabled}
                aria-current={state === "current" ? "step" : undefined}
                title={disabled ? t("coursewareAgent.workspace.lockedHint") : t(meta.label)}
              >
                <span className="st-step-dot" aria-hidden="true">
                  {state === "done" ? <StudioIcon name="check" size={13} /> : state === "locked" ? <StudioIcon name="lock" size={11} /> : <StudioIcon name={meta.icon} size={13} />}
                </span>
                <span className="st-step-label">{t(meta.label)}</span>
              </button>
            );
          })}
        </nav>

        <div className="st-topbar-actions">
          <button type="button" className="st-ghost-button" onClick={() => actions.navigate("present")} disabled={!pages.length}>
            <StudioIcon name="play" size={13} />
            <span>{t("coursewareAgent.workspace.present")}</span>
          </button>
          <button type="button" className="st-primary-button" onClick={actions.exportDeck} disabled={!hasDocuments || exporting}>
            {exporting ? t("coursewareAgent.workspace.exporting") : t("coursewareAgent.workspace.export")}
            <StudioIcon name={exporting ? "refresh" : "download"} size={14} className={exporting ? "is-spinning" : undefined} />
          </button>
        </div>
      </header>

      {(progress !== null || visualRunning) ? (
        <div className={`st-progress ${visualRunning && progress === null ? "is-indeterminate" : ""}`} role="status" aria-live="polite">
          <i style={progress !== null ? { width: `${Math.max(4, progress)}%` } : undefined} />
        </div>
      ) : <div className="st-progress is-idle" aria-hidden="true" />}

      <div className="st-workspace-body">{surfaceContent()}</div>
    </div>
  );
}
