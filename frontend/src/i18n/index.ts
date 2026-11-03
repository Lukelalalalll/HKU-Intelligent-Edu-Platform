/**
 * Public i18n surface.
 *
 * Feature code should import from this barrel rather than reaching into the
 * individual modules:
 *
 * ```tsx
 * const { t, locale, setLocale, formatDate } = useI18n();
 * t("courses.list.title");
 *
 * setLocale("yue");            // persists the choice
 * translate("errors.requestFailed"); // non-React helpers
 * ```
 */
export { DEFAULT_LOCALE, LOCALES, LOCALE_META, LOCALE_STORAGE_KEY, detectLocale, isLocale, readStoredLocale, type Locale, type LocaleMeta } from "./config";
export { formatDate, formatDateTimeLocal, formatNumber, type DateInput } from "./format";
export { I18nContext, I18nProvider, useI18n, type I18nValue } from "./I18nProvider";
export { getLocale, initLocale, setLocale, subscribeLocale } from "./localeStore";
export { createTranslator, interpolate, translate, type InterpolationValues, type TranslationKey, type Translator } from "./translate";
export { default as LanguageSelector } from "./LanguageSelector";
export type { Messages } from "./messages";
export { messages } from "./messages";
