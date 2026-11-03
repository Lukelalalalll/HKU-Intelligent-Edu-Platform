/**
 * Typed translation lookup.
 *
 * Keys are dot paths derived from the English message bundle, so a typo or a
 * deleted key fails ``tsc`` instead of silently rendering the raw key.
 */
import { DEFAULT_LOCALE, type Locale } from "./config";
import { getLocale } from "./localeStore";
import { messages, type Messages } from "./messages";

/** Values interpolated into ``{placeholder}`` slots. */
export type InterpolationValues = Record<string, string | number>;

type DotPaths<T> = {
  [K in keyof T & string]: T[K] extends string ? K : `${K}.${DotPaths<T[K]>}`;
}[keyof T & string];

/** Every valid translation key, e.g. ``"courses.detail.title"``. */
export type TranslationKey = DotPaths<Messages>;

/** Translate one key into the active locale. */
export type Translator = (key: TranslationKey, values?: InterpolationValues) => string;

const reportedMissingKeys = new Set<string>();

function reportMissingKey(locale: Locale, key: string): void {
  const id = `${locale}:${key}`;
  if (reportedMissingKeys.has(id)) return;
  reportedMissingKeys.add(id);
  if (import.meta.env.DEV) {
    // Surfacing the key keeps development builds honest without breaking users.
    console.warn(`[i18n] missing "${locale}" message for key "${key}"`);
  }
}

function lookup(locale: Locale, key: string): string | undefined {
  let node: unknown = messages[locale];
  for (const segment of key.split(".")) {
    if (!node || typeof node !== "object") return undefined;
    node = (node as Record<string, unknown>)[segment];
  }
  return typeof node === "string" ? node : undefined;
}

/** Replace ``{name}`` placeholders; unknown placeholders stay untouched. */
export function interpolate(template: string, values?: InterpolationValues): string {
  if (!values) return template;
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in values ? String(values[name]) : match));
}

const translators = new Map<Locale, Translator>();

/**
 * Build (and cache) a translator bound to one locale.
 *
 * Falls back to the source language and then English so a defensive lookup can
 * never crash the UI; in development the missing key is reported.
 */
export function createTranslator(locale: Locale): Translator {
  const cached = translators.get(locale);
  if (cached) return cached;
  const translator: Translator = (key, values) => {
    const message = lookup(locale, key) ?? lookup(DEFAULT_LOCALE, key) ?? lookup("en", key);
    if (message === undefined) {
      reportMissingKey(locale, key);
      return key;
    }
    return interpolate(message, values);
  };
  translators.set(locale, translator);
  return translator;
}

/**
 * Translate with the currently active locale.
 *
 * Use this from non-React helpers (API error normalization, formatters). React
 * components should use ``useI18n().t`` so they re-render on language change.
 */
export function translate(key: TranslationKey, values?: InterpolationValues): string {
  return createTranslator(getLocale())(key, values);
}
