import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../lib/apiClient", () => ({ api: { get } }));

import { clearAssetCache, invalidateAsset, isApiAsset, peekAssetUrl, resolveAssetUrl } from "./authedAssets";

describe("authedAssets", () => {
  let objectUrlIndex = 0;

  beforeEach(() => {
    clearAssetCache();
    get.mockReset();
    objectUrlIndex = 0;
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => `blob:asset-${++objectUrlIndex}`) });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  });

  it("detects API paths", () => {
    expect(isApiAsset("/api/ppt/file.png")).toBe(true);
    expect(isApiAsset("api/ppt/file.png")).toBe(true);
    expect(isApiAsset("https://example.com/file.png")).toBe(false);
    expect(isApiAsset(null)).toBe(false);
  });

  it("passes remote URLs through untouched", async () => {
    await expect(resolveAssetUrl("https://example.com/a.png")).resolves.toBe("https://example.com/a.png");
    expect(get).not.toHaveBeenCalled();
  });

  it("loads API assets through the authenticated client and caches them", async () => {
    get.mockResolvedValue({ data: new Blob(["x"]) });
    await expect(resolveAssetUrl("/api/ppt/a.png")).resolves.toBe("blob:asset-1");
    expect(get).toHaveBeenCalledWith("/ppt/a.png", { responseType: "blob" });
    expect(peekAssetUrl("/api/ppt/a.png")).toBe("blob:asset-1");

    await expect(resolveAssetUrl("/api/ppt/a.png")).resolves.toBe("blob:asset-1");
    expect(get).toHaveBeenCalledTimes(1);
  });

  it("resolves to null when the request fails and does not retry until invalidated", async () => {
    get.mockRejectedValue(new Error("401"));
    await expect(resolveAssetUrl("/api/ppt/missing.png")).resolves.toBeNull();
    await expect(resolveAssetUrl("/api/ppt/missing.png")).resolves.toBeNull();
    expect(get).toHaveBeenCalledTimes(1);

    get.mockResolvedValue({ data: new Blob(["x"]) });
    invalidateAsset("/api/ppt/missing.png");
    await expect(resolveAssetUrl("/api/ppt/missing.png")).resolves.toBe("blob:asset-1");
    expect(get).toHaveBeenCalledTimes(2);
  });

  it("clears cached object URLs", async () => {
    get.mockResolvedValue({ data: new Blob(["x"]) });
    await resolveAssetUrl("/api/ppt/a.png");
    clearAssetCache();
    expect(peekAssetUrl("/api/ppt/a.png")).toBeNull();
    await resolveAssetUrl("/api/ppt/a.png");
    expect(get).toHaveBeenCalledTimes(2);
  });
});
