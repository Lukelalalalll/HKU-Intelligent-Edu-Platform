import { afterEach, describe, expect, it } from "vitest";
import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, LOCALE_META, detectLocale, readStoredLocale, writeStoredLocale } from "./config";
import { getLocale, initLocale, setLocale, subscribeLocale } from "./localeStore";
import { messages } from "./messages";
import { createTranslator, interpolate, translate } from "./translate";

function keyPaths(value: unknown, prefix = ""): string[] {
  if (value === null || typeof value !== "object") return [prefix];
  return Object.entries(value as Record<string, unknown>)
    .flatMap(([key, child]) => keyPaths(child, prefix ? `${prefix}.${key}` : key))
    .sort();
}

afterEach(() => {
  setLocale(DEFAULT_LOCALE, { persist: false });
  window.localStorage.clear();
});

describe("locale metadata", () => {
  it("declares the three required languages with display metadata", () => {
    expect(LOCALE_META.en.nativeLabel).toBe("English");
    expect(LOCALE_META.yue.nativeLabel).toBe("粵語");
    expect(LOCALE_META["zh-Hans"].nativeLabel).toBe("简体中文");
  });
});

describe("browser language detection", () => {
  it("maps browser tags to supported locales", () => {
    expect(detectLocale(["en-US", "zh-CN"])).toBe("en");
    expect(detectLocale(["zh-HK"])).toBe("yue");
    expect(detectLocale(["yue-Hant-HK"])).toBe("yue");
    expect(detectLocale(["zh-CN"])).toBe("zh-Hans");
    expect(detectLocale(["zh-TW"])).toBe("zh-Hans");
    expect(detectLocale(["fr-FR"])).toBeNull();
  });

  it("falls back to the source language when nothing matches", () => {
    expect(detectLocale([]) ?? DEFAULT_LOCALE).toBe("zh-Hans");
  });
});

describe("locale store", () => {
  it("updates the document language and notifies once", () => {
    let notifications = 0;
    const unsubscribe = subscribeLocale(() => { notifications += 1; });
    setLocale("en", { persist: false });
    expect(getLocale()).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    // Re-selecting the active locale must not emit a redundant update.
    setLocale("en", { persist: false });
    expect(notifications).toBe(1);
    unsubscribe();
  });

  it("persists explicit choices and restores them at boot", () => {
    setLocale("yue");
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe("yue");
    setLocale(DEFAULT_LOCALE, { persist: false });
    expect(initLocale()).toBe("yue");
  });

  it("ignores unavailable or corrupted storage", () => {
    expect(readStoredLocale({ getItem: () => "klingon" })).toBeNull();
    expect(readStoredLocale({ getItem: () => null })).toBeNull();
    expect(() => writeStoredLocale("en", { setItem: () => { throw new Error("quota"); } })).not.toThrow();
  });
});

describe("translation", () => {
  it("interpolates named placeholders", () => {
    expect(createTranslator("en")("shared.fileUploader.status.extracting", { progress: 42 })).toBe("Parsing 42%");
    expect(interpolate("你好，{name}", { name: "陳同學" })).toBe("你好，陳同學");
    expect(interpolate("keep {unknown}", {})).toBe("keep {unknown}");
  });

  it("translates the active locale from non-React helpers", () => {
    setLocale("yue", { persist: false });
    expect(translate("common.header.language")).toBe("語言");
    setLocale("en", { persist: false });
    expect(translate("common.header.language")).toBe("Language");
  });

  it("keeps every locale structurally identical to English", () => {
    const englishKeys = keyPaths(messages.en);
    expect(keyPaths(messages["zh-Hans"])).toEqual(englishKeys);
    expect(keyPaths(messages.yue)).toEqual(englishKeys);
  });

  it("never ships the raw key for a known message", () => {
    for (const locale of ["en", "yue", "zh-Hans"] as const) {
      const value = createTranslator(locale)("common.header.logout");
      expect(value.length).toBeGreaterThan(0);
      expect(value).not.toBe("common.header.logout");
    }
  });
});
