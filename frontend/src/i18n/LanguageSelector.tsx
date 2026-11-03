/**
 * Header language switcher.
 *
 * A disclosure menu (ARIA ``menu``/``menuitemradio``) that lists every supported
 * language, marks the active one and writes the choice through the locale store.
 * Keyboard support: Enter/Space open, Arrow keys move, Home/End jump, Escape
 * closes and returns focus, Tab closes.
 */
import React from "react";
import { LOCALES, LOCALE_META, type Locale } from "./config";
import { useI18n } from "./I18nProvider";
import "./LanguageSelector.css";

const stepIndex = (index: number, delta: number) => (index + delta + LOCALES.length) % LOCALES.length;

/** Language dropdown placed at the right edge of the site header. */
export default function LanguageSelector({ className = "" }: { className?: string }) {
  const { locale, setLocale, t } = useI18n();
  const [open, setOpen] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(() => Math.max(0, LOCALES.indexOf(locale)));
  const rootRef = React.useRef<HTMLDivElement | null>(null);
  const triggerRef = React.useRef<HTMLButtonElement | null>(null);
  const optionRefs = React.useRef<Array<HTMLButtonElement | null>>([]);
  const menuId = React.useId();
  const activeMeta = LOCALE_META[locale];

  const close = React.useCallback((restoreFocus = false) => {
    setOpen(false);
    if (restoreFocus) triggerRef.current?.focus();
  }, []);

  const openMenu = React.useCallback(() => {
    setActiveIndex(Math.max(0, LOCALES.indexOf(locale)));
    setOpen(true);
  }, [locale]);

  const focusOption = React.useCallback((index: number) => {
    setActiveIndex(index);
    optionRefs.current[index]?.focus();
  }, []);

  const choose = React.useCallback((next: Locale) => {
    setLocale(next);
    setOpen(false);
    triggerRef.current?.focus();
  }, [setLocale]);

  // Close on outside pointer interactions while preserving in-menu clicks.
  React.useEffect(() => {
    if (!open) return undefined;
    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) close();
    };
    document.addEventListener("pointerdown", handlePointerDown);
    return () => document.removeEventListener("pointerdown", handlePointerDown);
  }, [close, open]);

  // Focus the selected option when the menu opens.
  React.useEffect(() => {
    if (!open) return;
    optionRefs.current[Math.max(0, LOCALES.indexOf(locale))]?.focus();
    // Intentionally keyed on ``open`` only: arrow-key navigation manages its own focus.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && open) {
      event.preventDefault();
      close(true);
      return;
    }
    if (!open) return;
    if (event.key === "ArrowDown") {
      event.preventDefault();
      focusOption(stepIndex(activeIndex, 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      focusOption(stepIndex(activeIndex, -1));
    } else if (event.key === "Home") {
      event.preventDefault();
      focusOption(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusOption(LOCALES.length - 1);
    } else if (event.key === "Tab") {
      close();
    }
  };

  return (
    <div className={`language-selector ${className}`.trim()} ref={rootRef} onKeyDown={handleKeyDown}>
      <button
        ref={triggerRef}
        type="button"
        className="language-trigger"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        aria-label={`${t("common.header.language")}: ${activeMeta.nativeLabel}`}
        onClick={() => (open ? close() : openMenu())}
      >
        <i className="fas fa-globe language-icon" aria-hidden="true" />
        <span className="language-trigger-label" lang={activeMeta.htmlLang}>{activeMeta.nativeLabel}</span>
        <i className="fas fa-chevron-down language-chevron" aria-hidden="true" />
      </button>

      {open ? (
        <div className="language-menu" id={menuId} role="menu" aria-label={t("common.header.language")}>
          <p className="language-menu-heading" role="presentation">{t("common.header.language")}</p>
          {LOCALES.map((option, index) => {
            const meta = LOCALE_META[option];
            const selected = option === locale;
            return (
              <button
                key={option}
                ref={(node) => { optionRefs.current[index] = node; }}
                type="button"
                role="menuitemradio"
                aria-checked={selected}
                tabIndex={index === activeIndex ? 0 : -1}
                className={`language-option ${selected ? "is-selected" : ""}`}
                onClick={() => choose(option)}
                onFocus={() => setActiveIndex(index)}
              >
                <span className="language-option-text">
                  <span className="language-option-label" lang={meta.htmlLang}>{meta.nativeLabel}</span>
                  <span className="language-option-hint" lang="en">{meta.englishLabel}</span>
                </span>
                {selected ? <i className="fas fa-check language-check" aria-hidden="true" /> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
