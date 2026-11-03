/**
 * Locale-aware date and number formatting.
 *
 * Components receive bound versions from ``useI18n()``; non-React helpers can
 * pass a locale explicitly or use the active one.
 */
import { LOCALE_META, type Locale } from "./config";
import { getLocale } from "./localeStore";

/** Anything ``Date`` accepts that the UI is likely to format. */
export type DateInput = Date | string | number;

const dateFormatterCache = new Map<string, Intl.DateTimeFormat>();
const numberFormatterCache = new Map<string, Intl.NumberFormat>();

function toDate(value: DateInput): Date | null {
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Format a date with the locale's BCP-47 tag; invalid input renders as ``""``. */
export function formatDate(locale: Locale, value: DateInput, options?: Intl.DateTimeFormatOptions): string {
  const date = toDate(value);
  if (!date) return "";
  const resolved: Intl.DateTimeFormatOptions = options ?? { year: "numeric", month: "short", day: "numeric" };
  const cacheKey = `${locale}:${JSON.stringify(resolved)}`;
  let formatter = dateFormatterCache.get(cacheKey);
  if (!formatter) {
    formatter = new Intl.DateTimeFormat(LOCALE_META[locale].intlTag, resolved);
    dateFormatterCache.set(cacheKey, formatter);
  }
  return formatter.format(date);
}

/** Format a number with the locale's BCP-47 tag. */
export function formatNumber(locale: Locale, value: number, options?: Intl.NumberFormatOptions): string {
  const cacheKey = `${locale}:${JSON.stringify(options ?? {})}`;
  let formatter = numberFormatterCache.get(cacheKey);
  if (!formatter) {
    formatter = new Intl.NumberFormat(LOCALE_META[locale].intlTag, options);
    numberFormatterCache.set(cacheKey, formatter);
  }
  return formatter.format(value);
}

/** Format a date and time for the active locale (non-React convenience). */
export function formatDateTimeLocal(value: DateInput, options?: Intl.DateTimeFormatOptions): string {
  return formatDate(getLocale(), value, options ?? { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
