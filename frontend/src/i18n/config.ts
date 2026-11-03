/**
 * Locale catalogue and persistence helpers.
 *
 * Supported languages ship as first-class UI locales:
 * - ``en``      English (Hong Kong)
 * - ``yue``     Cantonese (written Traditional Chinese, 粵文)
 * - ``zh-Hans`` Simplified Chinese (source language, used as the safe default)
 *
 * Adding a locale later only requires a new entry here plus a messages bundle in
 * ``./messages/<namespace>.ts``. TypeScript then enforces key parity everywhere.
 */

/** Every supported UI locale, in the order shown in the language menu. */
export const LOCALES = ["en", "yue", "zh-Hans"] as const;

/** Union of supported locale identifiers. */
export type Locale = (typeof LOCALES)[number];

/**
 * Locale used when nothing is stored or detected.
 *
 * The product copy was originally written in Simplified Chinese, so it doubles
 * as the safe fallback for SSR, tests and first paint.
 */
export const DEFAULT_LOCALE: Locale = "zh-Hans";

/** localStorage key that remembers an explicit user choice. */
export const LOCALE_STORAGE_KEY = "hku-intelligent-edu.locale";

/** Display and formatting metadata for one locale. */
export type LocaleMeta = {
  /** Name shown in the selector, always written in the locale itself. */
  nativeLabel: string;
  /** English name used as a secondary hint inside the menu. */
  englishLabel: string;
  /** Value applied to ``<html lang>``. */
  htmlLang: string;
  /** BCP-47 tag used by Intl for dates and numbers. */
  intlTag: string;
};

/** Metadata for every locale; keep in sync with {@link LOCALES}. */
export const LOCALE_META: Record<Locale, LocaleMeta> = {
  en: { nativeLabel: "English", englishLabel: "English", htmlLang: "en", intlTag: "en-HK" },
  yue: { nativeLabel: "粵語", englishLabel: "Cantonese", htmlLang: "yue", intlTag: "zh-HK" },
  "zh-Hans": { nativeLabel: "简体中文", englishLabel: "Simplified Chinese", htmlLang: "zh-Hans", intlTag: "zh-CN" },
};

/** Type guard for values read from storage or the URL. */
export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (LOCALES as readonly string[]).includes(value);
}

/**
 * Read the persisted locale, ignoring unavailable or corrupted storage.
 */
export function readStoredLocale(storage?: Pick<Storage, "getItem">): Locale | null {
  try {
    const source = storage ?? (typeof window !== "undefined" ? window.localStorage : undefined);
    const value = source?.getItem(LOCALE_STORAGE_KEY);
    return isLocale(value) ? value : null;
  } catch {
    return null;
  }
}

/**
 * Persist an explicit language choice; storage failures (private mode, quota)
 * must never break rendering.
 */
export function writeStoredLocale(locale: Locale, storage?: Pick<Storage, "setItem">): void {
  try {
    const target = storage ?? (typeof window !== "undefined" ? window.localStorage : undefined);
    target?.setItem(LOCALE_STORAGE_KEY, locale);
  } catch {
    // A failed preference write is harmless: the next visit re-detects.
  }
}

/**
 * Best-effort match of the browser's preferred languages.
 *
 * ``zh-HK``/``zh-MO`` browsers are mapped to Cantonese because Hong Kong users
 * expect Traditional Chinese, and ``yue*`` tags are unambiguous. Other Chinese
 * tags fall back to Simplified Chinese.
 */
export function detectLocale(languages?: readonly string[]): Locale | null {
  const candidates = languages ?? (typeof navigator !== "undefined" ? navigator.languages ?? [navigator.language] : []);
  for (const candidate of candidates) {
    const tag = String(candidate ?? "").trim().toLowerCase();
    if (!tag) continue;
    if (tag.startsWith("yue") || tag === "zh-hk" || tag.startsWith("zh-hk-") || tag === "zh-mo" || tag.startsWith("zh-mo-")) {
      return "yue";
    }
    if (tag.startsWith("zh")) return "zh-Hans";
    if (tag === "en" || tag.startsWith("en-")) return "en";
  }
  return null;
}
