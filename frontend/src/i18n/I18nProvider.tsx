/**
 * React binding for the locale store.
 *
 * The provider subscribes React to the external locale store and exposes one
 * stable object with the translator plus locale-bound formatters, so every
 * descendant re-renders correctly when the language changes.
 */
import React from "react";
import { DEFAULT_LOCALE, LOCALE_META, type Locale, type LocaleMeta } from "./config";
import { formatDate, formatNumber, type DateInput } from "./format";
import { getLocale, setLocale, subscribeLocale } from "./localeStore";
import { createTranslator, type Translator } from "./translate";

/** Value shared through {@link I18nContext}. */
export type I18nValue = {
  /** Active locale. */
  locale: Locale;
  /** Display metadata for the active locale. */
  localeMeta: LocaleMeta;
  /** Switch language; persists an explicit choice to localStorage. */
  setLocale: (locale: Locale) => void;
  /** Translate a key into the active locale. */
  t: Translator;
  /** Format a date with the active locale. */
  formatDate: (value: DateInput, options?: Intl.DateTimeFormatOptions) => string;
  /** Format a number with the active locale. */
  formatNumber: (value: number, options?: Intl.NumberFormatOptions) => string;
};

const fallbackTranslator = createTranslator(DEFAULT_LOCALE);

/**
 * Default context value used when a component renders outside the provider
 * (isolated component tests, static markup). The source language keeps those
 * renders deterministic.
 */
export const I18nContext = React.createContext<I18nValue>({
  locale: DEFAULT_LOCALE,
  localeMeta: LOCALE_META[DEFAULT_LOCALE],
  setLocale,
  t: fallbackTranslator,
  formatDate: (value, options) => formatDate(DEFAULT_LOCALE, value, options),
  formatNumber: (value, options) => formatNumber(DEFAULT_LOCALE, value, options),
});

/** Subscribe the React tree to the active locale. */
export function I18nProvider({ children }: { children: React.ReactNode }) {
  const locale = React.useSyncExternalStore(subscribeLocale, getLocale, () => DEFAULT_LOCALE);

  const value = React.useMemo<I18nValue>(() => ({
    locale,
    localeMeta: LOCALE_META[locale],
    setLocale,
    t: createTranslator(locale),
    formatDate: (date, options) => formatDate(locale, date, options),
    formatNumber: (number, options) => formatNumber(locale, number, options),
  }), [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

/** Access the active locale, translator and formatters. */
export function useI18n(): I18nValue {
  return React.useContext(I18nContext);
}
