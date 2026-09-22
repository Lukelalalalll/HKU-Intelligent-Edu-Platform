import { describe, expect, it } from "vitest";
import { getApiErrorMessage, toApiError } from "./apiClient";

describe("api client error normalization", () => {
  it("keeps useful status and retry information", () => {
    const error = toApiError({ response: { status: 503, data: { detail: "服务暂时不可用", code: "upstream" } }, message: "bad gateway", isAxiosError: true });
    expect(error).toMatchObject({ status: 503, code: "upstream", message: "服务暂时不可用", retryable: true });
  });

  it("provides a stable fallback for unknown errors", () => {
    expect(getApiErrorMessage({})).toBe("请求失败，请稍后重试");
    expect(getApiErrorMessage(new Error("boom"))).toBe("boom");
  });
});
