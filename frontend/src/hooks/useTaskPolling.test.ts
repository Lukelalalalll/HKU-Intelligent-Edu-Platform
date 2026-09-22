import { describe, expect, it } from "vitest";
import { isTerminalTaskStatus } from "./useTaskPolling";

describe("task lifecycle", () => {
  it("recognizes every terminal status", () => {
    expect(isTerminalTaskStatus("completed")).toBe(true);
    expect(isTerminalTaskStatus("completed_with_errors")).toBe(true);
    expect(isTerminalTaskStatus("failed")).toBe(true);
    expect(isTerminalTaskStatus("cancelled")).toBe(true);
    expect(isTerminalTaskStatus("running")).toBe(false);
  });
});
