import { describe, expect, it } from "vitest";
import { answerList, answerNumber, answerText, documentMarkdown, downloadFilename, materialFileIssue, stageKey } from "./lessonPlanFormat";

describe("lessonPlanFormat", () => {
  it("reads version-2 markdown documents", () => {
    expect(documentMarkdown({ version: 2, markdown: "  - 目标  " })).toBe("- 目标");
  });

  it("falls back to legacy canvas elements", () => {
    const markdown = documentMarkdown({ elements: [{ type: "title", text: "学习目标" }, { type: "body", text: "要点" }] });
    expect(markdown).toContain("学习目标");
    expect(markdown).toContain("要点");
  });

  it("rejects unsupported and oversized material files", () => {
    expect(materialFileIssue(new File(["x"], "notes.exe"))).toBe("type");
    expect(materialFileIssue(new File(["x"], "notes.md"))).toBeNull();
    const big = { name: "big.pdf", size: 51 * 1024 * 1024 } as File;
    expect(materialFileIssue(big)).toBe("size");
  });

  it("builds a safe download filename", () => {
    const name = downloadFilename("牛顿第二定律 / 学案", "pdf");
    expect(name).toMatch(/\.pdf$/);
    expect(name).not.toContain("/");
  });

  it("coerces answer helpers", () => {
    expect(answerList(["a", " ", "b"])).toEqual(["a", "b"]);
    expect(answerList("单条")).toEqual(["单条"]);
    expect(answerText(45)).toBe("45");
    expect(answerNumber("45")).toBe(45);
    expect(answerNumber("abc")).toBeNull();
  });

  it("maps stages to translation keys", () => {
    expect(stageKey("outline")).toBe("lessonPlan.stage.outline");
    expect(stageKey("unknown")).toBe("lessonPlan.stage.collecting");
  });
});
