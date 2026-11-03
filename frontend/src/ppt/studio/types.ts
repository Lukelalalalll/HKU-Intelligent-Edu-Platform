/**
 * Shared contracts for the courseware studio surfaces.
 *
 * The page component owns every request and mutation; surfaces stay
 * presentational and receive one typed model object.
 */
import type {
  PptDocument,
  PptMessage,
  PptPage,
  PptPagePatch,
  PptProject,
  PptRequirement,
  PptSource,
  PptTheme,
  RequirementChatResponse,
} from "../../api";

/** Every surface the studio can render. */
export type StudioSurface = "start" | "outline" | "visual" | "theme" | "layouting" | "editor" | "present";

/** Surfaces that appear as a step in the workspace stepper. */
export type StepSurface = Extract<StudioSurface, "start" | "outline" | "visual" | "theme" | "editor">;

/** Progress state of one stepper entry. */
export type StepState = "done" | "current" | "available" | "locked";

/** PPT export request state. */
export type ExportState = "idle" | "exporting";

/** Layout generation state mirrored from ``usePptGeneration``. */
export type LayoutState = { running: boolean; progress: number; error: string | null };

/** Read-only data handed to every surface. */
export type StudioData = {
  project: PptProject;
  pages: PptPage[];
  selected: number;
  messages: PptMessage[];
  requirement: PptRequirement | null;
  sources: PptSource[];
  themes: PptTheme[];
  surface: StudioSurface;
  /** Long-running outline generation. */
  outlineGenerating: boolean;
  /** Visual batch research in flight. */
  visualRunning: boolean;
  layout: LayoutState;
  exportState: ExportState;
  autosaveSaving: boolean;
};

/** Mutations the surfaces may request. */
export type StudioActions = {
  navigate: (surface: StudioSurface) => void;
  goHome: () => void;
  selectPage: (index: number) => void;
  refresh: () => Promise<unknown>;
  refreshMessages: () => Promise<unknown>;
  generateOutline: () => void;
  confirmOutline: () => void;
  reorderPages: (ids: string[]) => void;
  patchPage: (page: PptPage, payload: PptPagePatch) => Promise<PptPage>;
  runVisualResearch: () => void;
  saveVisualSelection: (page: PptPage, ids: string[]) => Promise<void>;
  generateDeck: (themeId?: string) => void;
  retryDesign: () => void;
  scheduleSave: (page: PptPage, document: PptDocument) => void;
  flushAutosave: () => Promise<void>;
  exportDeck: () => void;
  uploadFiles: (files: FileList | File[]) => void;
  updateRequirement: (response: RequirementChatResponse) => void;
};

/** One model object for every workspace surface. */
export type StudioModel = StudioData & { actions: StudioActions };
