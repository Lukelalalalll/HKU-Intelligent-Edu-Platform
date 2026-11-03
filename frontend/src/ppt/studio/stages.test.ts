import { describe, expect, it } from "vitest";
import type { PptPage, PptProject } from "../../api";
import { defaultSurface, stageKey, stageRank, stepStates } from "./stages";

const project = (patch: Partial<PptProject> = {}): PptProject => ({
  id: "project-1",
  title: "Test deck",
  request_text: "Teach something",
  current_stage: "init",
  page_count_target: 10,
  page_count: 0,
  design_status: "pending",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  ...patch,
} as PptProject);

const page = (patch: Partial<PptPage> = {}): PptPage => ({
  id: `page-${Math.random().toString(36).slice(2)}`,
  project_id: "project-1",
  section_title: "Section",
  sort_order: 0,
  title: "Page",
  bullets: ["Point"],
  statuses: {},
  search_queries: [],
  summary_md: "",
  citations: [],
  document: null,
  speaker_notes: "",
  ...patch,
} as PptPage);

describe("stageRank", () => {
  it("orders backend stages", () => {
    expect(stageRank("init")).toBe(0);
    expect(stageRank("outline")).toBe(1);
    expect(stageRank("visual")).toBe(2);
    expect(stageRank("design")).toBe(5);
    expect(stageRank("export")).toBe(6);
    expect(stageRank(undefined)).toBe(0);
    expect(stageRank("unknown")).toBe(0);
  });
});

describe("stepStates", () => {
  it("locks every later step while there are no pages", () => {
    const states = stepStates(project(), [], "start");
    expect(states.start).toBe("current");
    expect(states.outline).toBe("locked");
    expect(states.visual).toBe("locked");
    expect(states.theme).toBe("locked");
    expect(states.editor).toBe("locked");
  });

  it("marks the active step as current even when its data is complete", () => {
    const pages = [page({ document: { elements: [] } as PptPage["document"] })];
    const states = stepStates(project({ current_stage: "design", design_status: "ready", theme_id: "dark" }), pages, "outline");
    expect(states.outline).toBe("current");
    expect(states.start).toBe("done");
    expect(states.visual).toBe("done");
    expect(states.theme).toBe("done");
    expect(states.editor).toBe("done");
  });

  it("kills the editor until a document exists", () => {
    const states = stepStates(project({ current_stage: "theme", theme_id: "dark" }), [page()], "theme");
    expect(states.editor).toBe("locked");
    expect(states.theme).toBe("current");
  });
});

describe("defaultSurface", () => {
  it("starts at requirements without pages", () => {
    expect(defaultSurface(project(), [])).toBe("start");
  });

  it("opens the outline once pages exist", () => {
    expect(defaultSurface(project({ current_stage: "outline" }), [page()])).toBe("outline");
  });

  it("opens visuals for the visual stage and theme afterwards", () => {
    expect(defaultSurface(project({ current_stage: "visual" }), [page()])).toBe("visual");
    expect(defaultSurface(project({ current_stage: "theme", theme_id: "dark" }), [page()])).toBe("theme");
  });

  it("opens the editor as soon as a page has a document", () => {
    const pages = [page({ document: { elements: [] } as PptPage["document"] })];
    expect(defaultSurface(project({ current_stage: "design" }), pages)).toBe("editor");
  });
});

describe("stageKey", () => {
  it("falls back to the in-progress label", () => {
    expect(stageKey("init")).toBe("coursewareAgent.stages.init");
    expect(stageKey("something-new")).toBe("coursewareAgent.stages.inProgress");
    expect(stageKey(null)).toBe("coursewareAgent.stages.init");
  });
});
