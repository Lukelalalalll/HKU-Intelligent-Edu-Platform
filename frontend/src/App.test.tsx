import { describe, expect, it } from "vitest";
import { SUPPORTED_ROLES } from "./api";

describe("Phase 1 frontend", () => {
  it("declares the three supported roles in the API contract", () => {
    expect(SUPPORTED_ROLES).toEqual(["teacher", "student", "admin"]);
  });
});
