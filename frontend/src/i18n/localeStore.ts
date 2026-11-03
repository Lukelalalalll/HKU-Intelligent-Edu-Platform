/**
 * Tiny external store for the active locale.
 *
 * Living outside React lets non-component helpers (API error normalization,
 * formatting utilities) translate with the same language as the UI, while
 * ``useSyncExternalStore`` in the provider keeps React renders in sync.
 */
import { DEFAULT_LOCALE, LOCALE_META, detectLocale, readStoredLocale, writeStoredLocale, type Locale } from "./config";

let currentLocale: Locale = DEFAULT_LOCALE;
const listeners = new Set<() => void>();

/**
 * Apply the locale to the document so browsers, screen readers and CSS
 * ``:lang()`` selectors see the current language.
 */
function applyDocumentLang(locale: Locale): void {
  if (typeof document === "undefined") return;
  document.documentElement.lang = LOCALE_META[locale].htmlLang;
}

/** Current locale for non-React code. */
export function getLocale(): Locale {
  return currentLocale;
}

/** Subscribe to locale changes; returns the unsubscribe function. */
export function subscribeLocale(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/**
 * Change the active locale.
 *
 * @param locale  Target locale.
 * @param options ``persist: false`` skips localStorage (used for detected defaults
 *                so the next visit can re-detect the browser language).
 */
export function setLocale(locale: Locale, options: { persist?: boolean } = {}): void {
  const persist = options.persist ?? true;
  if (persist) writeStoredLocale(locale);
  applyDocumentLang(locale);
  if (locale === currentLocale) return;
  currentLocale = locale;
  listeners.forEach((listener) => listener());
}

/**
 * Initialize the locale once at application boot: explicit choice first, then
 * browser detection, then the source-language default.
 */
export function initLocale(): Locale {
  const initial = readStoredLocale() ?? detectLocale() ?? DEFAULT_LOCALE;
  setLocale(initial, { persist: false });
  return initial;
}
