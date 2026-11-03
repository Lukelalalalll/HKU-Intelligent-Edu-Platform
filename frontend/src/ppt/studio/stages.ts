/**
 * Pure helpers that turn project data into stepper state.
 *
 * Keeping this logic outside React makes the flow rules testable and keeps the
 * page component free of conditional rendering decisions.
 */
import type { PptPage, PptProject } from "../../api";
import type { TranslationKey } from "../../i18n";
import type { StepState, StepSurface, StudioSurface } from "./types";

/** Backend stage codes mapped to their display label. */
export const STAGE_KEYS: Record<string, TranslationKey> = {
  init: "coursewareAgent.stages.init",
  outline: "coursewareAgent.stages.outline",
  visual: "coursewareAgent.stages.visual",
  theme: "coursewareAgent.stages.theme",
  layout: "coursewareAgent.stages.layout",
  design: "coursewareAgent.stages.design",
  export: "coursewareAgent.stages.export",
};

/** Translation key for a backend stage code. */
export function stageKey(stage?: string | null): TranslationKey {
  return STAGE_KEYS[String(stage || "init")] ?? "coursewareAgent.stages.inProgress";
}

/** Backend stage order used for "already passed this step" checks. */
const STAGE_ORDER = ["init", "outline", "visual", "theme", "layout", "design", "export"] as const;

/** Zero-based position of a backend stage code. */
export function stageRank(stage?: string | null): number {
  const index = STAGE_ORDER.indexOf(String(stage || "init") as (typeof STAGE_ORDER)[number]);
  return index < 0 ? 0 : index;
}

/** Steps shown in the workspace stepper, in order. */
export const STEP_ORDER: StepSurface[] = ["start", "outline", "visual", "theme", "editor"];

/** True when the stepper entry can be opened. */
export function canOpenStep(state: StepState): boolean {
  return state !== "locked";
}

function hasVisuals(pages: PptPage[]): boolean {
  if (!pages.length) return false;
  return pages.every((page) => {
    const status = page.statuses?.visual;
    const assetStatus = page.visual_plan?.asset_status;
    return status === "ready" || status === "degraded" || assetStatus === "ready" || (page.asset_manifest?.length ?? 0) > 0;
  });
}

/**
 * Resolve each step to done / current / available / locked.
 *
 * The active step is always "current" even when its data already looks done,
 * because the user is looking at it.
 */
export function stepStates(project: PptProject | null, pages: PptPage[], active: StepSurface): Record<StepSurface, StepState> {
  const hasPages = pages.length > 0;
  const hasDocuments = pages.some((page) => Boolean(page.document));
  const rank = stageRank(project?.current_stage);
  const outlineDone = hasPages && (rank >= 2 || Boolean(project?.latest_checkpoint_code?.includes("outline")));
  const visualDone = rank >= 3 || (rank >= 2 && hasVisuals(pages));
  const themeChosen = Boolean(project?.theme_id);
  const themeDone = themeChosen && (rank >= 5 || project?.design_status === "ready");
  const editorDone = hasDocuments && (rank >= 5 || project?.design_status === "ready");

  const state: Record<StepSurface, StepState> = {
    start: outlineDone ? "done" : "available",
    outline: !hasPages ? "locked" : outlineDone ? "done" : "available",
    visual: !hasPages ? "locked" : visualDone ? "done" : "available",
    theme: !hasPages ? "locked" : themeDone ? "done" : "available",
    editor: !hasDocuments ? "locked" : editorDone ? "done" : "available",
  };
  state[active] = "current";
  return state;
}

/**
 * Pick the surface a project should open on.
 *
 * Designed pages open in the editor; otherwise the deepest unfinished step is
 * chosen without triggering any background job.
 */
export function defaultSurface(project: PptProject | null, pages: PptPage[]): StudioSurface {
  if (!project) return "start";
  const rank = stageRank(project.current_stage);
  if (pages.some((page) => Boolean(page.document))) return "editor";
  if (!pages.length) return "start";
  if (rank >= 3) return "theme";
  if (rank === 2) return "visual";
  return "outline";
}

/** Human-readable index of one step (1-based). */
export function stepNumber(step: StepSurface): number {
  return Math.max(1, STEP_ORDER.indexOf(step) + 1);
}
