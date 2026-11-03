/**
 * Theme surface: real layout previews, explicit design generation.
 */
import React, { useEffect, useMemo, useState } from "react";
import { pptApi, type PptTheme } from "../../api";
import { useI18n } from "../../i18n";
import AuthedImage from "../../shared/components/AuthedImage";
import { HKUConfirmDialog } from "../../shared/components/HKUDialog";
import { StudioIcon } from "./icons";
import type { StudioModel } from "./types";

export type ThemeSurfaceProps = { model: StudioModel };
const FAMILY_ALL = "all";

/** Theme gallery + generate action. */
export default function ThemeSurface({ model }: ThemeSurfaceProps) {
  const { t } = useI18n();
  const { project, themes, pages, layout, actions } = model;
  const [query, setQuery] = useState("");
  const [family, setFamily] = useState(FAMILY_ALL);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [themeChoice, setThemeChoice] = useState<string | null>(project.theme_id || null);
  const families = useMemo(() => Array.from(new Set(themes.map((theme) => theme.family).filter(Boolean))), [themes]);
  const visible = themes.filter((theme) => {
    const matchesFamily = family === FAMILY_ALL || theme.family === family;
    const haystack = `${theme.name} ${theme.description}`.toLowerCase();
    return matchesFamily && haystack.includes(query.trim().toLowerCase());
  });
  const hasDocuments = pages.some((page) => Boolean(page.document));
  const selectedTheme = themeChoice;
  const busy = layout.running;

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const entries = await Promise.all(themes.map(async (theme: PptTheme) => {
        if (previews[theme.id]) return null;
        try {
          const { data } = await pptApi.layouts(theme.id);
          const layoutId = data.items?.[0]?.id;
          if (!layoutId) return null;
          return [theme.id, `/api/ppt/themes/${theme.id}/layouts/${layoutId}/preview.svg`] as const;
        } catch {
          return null;
        }
      }));
      if (cancelled) return;
      const next = entries.filter(Boolean) as (readonly [string, string])[];
      if (next.length) setPreviews((current) => ({ ...current, ...Object.fromEntries(next) }));
    };
    if (themes.length) void load();
    return () => { cancelled = true; };
    // Previews are cached per theme id; re-running when the theme list changes is enough.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [themes]);

  const choose = (theme: PptTheme) => {
    if (busy) return;
    setThemeChoice(theme.id);
  };

  const generate = () => {
    if (busy || !themeChoice) return;
    if (hasDocuments) setConfirmOpen(true);
    else actions.generateDeck(themeChoice);
  };

  return (
    <div className="st-surface st-theme" data-testid="studio-surface-theme">
      <header className="st-surface-head">
        <div>
          <span className="st-eyebrow">04 · {t("coursewareAgent.workspace.steps.theme")}</span>
          <h2>{t("coursewareAgent.theme.title")}</h2>
          <p>{t("coursewareAgent.theme.subtitle")}</p>
        </div>
        <span className={`st-state-pill ${selectedTheme ? "is-ready" : ""}`}>
          <i aria-hidden="true" /> {selectedTheme ? themes.find((theme) => theme.id === selectedTheme)?.name || selectedTheme : t("coursewareAgent.theme.none")}
        </span>
      </header>

      <div className="st-surface-body st-theme-body">
        <div className="st-theme-toolbar">
          <label className="st-search">
            <StudioIcon name="search" size={15} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t("coursewareAgent.theme.searchPlaceholder")} />
          </label>
          <div className="st-segmented" role="group">
            {[FAMILY_ALL, ...families].map((item) => (
              <button key={item} type="button" className={family === item ? "is-active" : ""} onClick={() => setFamily(item)}>
                {item === FAMILY_ALL ? t("coursewareAgent.theme.allFamilies") : item}
              </button>
            ))}
          </div>
        </div>

        {visible.length ? (
          <div className="st-theme-grid">
            {visible.map((theme) => {
              const active = theme.id === selectedTheme;
              const preview = previews[theme.id];
              return (
                <button
                  key={theme.id}
                  type="button"
                  className={`st-theme-card ${active ? "is-selected" : ""}`}
                  onClick={() => choose(theme)}
                  disabled={busy}
                  aria-pressed={active}
                >
                  <span className="st-theme-preview" style={{ background: theme.colors?.bg || "#f3f6f2" }}>
                    {preview ? (
                      <AuthedImage
                        src={preview}
                        alt={theme.name}
                        placeholder={<ThemeSwatch theme={theme} />}
                      />
                    ) : <ThemeSwatch theme={theme} />}
                    <span className="st-theme-check" aria-hidden="true">{active ? <StudioIcon name="check" size={13} /> : null}</span>
                  </span>
                  <span className="st-theme-info">
                    <strong>{theme.name}</strong>
                    <small>{theme.description}</small>
                    <em>
                      {theme.family}
                      <i aria-hidden="true" />
                      {t("coursewareAgent.theme.layouts", { count: theme.layout_count || 0 })}
                      <i aria-hidden="true" />
                      {theme.accessibility?.passes ? t("coursewareAgent.theme.highContrast") : t("coursewareAgent.theme.needsCheck")}
                    </em>
                  </span>
                </button>
              );
            })}
          </div>
        ) : (
          <div className="st-empty-block">
            <span aria-hidden="true"><StudioIcon name="palette" size={22} /></span>
            <p>{t("coursewareAgent.theme.previewFailed")}</p>
          </div>
        )}
      </div>

      <footer className="st-surface-foot">
        <span className="st-foot-hint">{t("coursewareAgent.theme.generateHint")}</span>
        <div className="st-foot-actions">
          <button type="button" className="st-ghost-button" onClick={() => actions.navigate("visual")}>
            <StudioIcon name="back" size={14} /> {t("coursewareAgent.workspace.back")}
          </button>
          <button type="button" className="st-primary-button" onClick={generate} disabled={!selectedTheme || busy}>
            {busy ? t("coursewareAgent.theme.generating") : t("coursewareAgent.theme.generate")}
            <StudioIcon name={busy ? "refresh" : "wand"} size={15} className={busy ? "is-spinning" : undefined} />
          </button>
        </div>
      </footer>

      <HKUConfirmDialog
        open={confirmOpen}
        scope="viewport"
        title={t("coursewareAgent.theme.overwriteTitle")}
        description={t("coursewareAgent.theme.overwriteDescription")}
        confirmLabel={t("coursewareAgent.theme.overwriteConfirm")}
        confirmTone="primary"
        onClose={() => setConfirmOpen(false)}
        onConfirm={() => { setConfirmOpen(false); actions.generateDeck(themeChoice || undefined); }}
      />
    </div>
  );
}

/** Token swatch used before a preview loads or when it fails. */
function ThemeSwatch({ theme }: { theme: PptTheme }) {
  const colors = theme.colors || {};
  return (
    <span className="st-theme-swatch" aria-hidden="true" style={{ background: colors.bg || "#eef3ee" }}>
      <b style={{ background: colors.title || "#173f32" }} />
      <b style={{ background: colors.accent || "#4c9c78" }} />
      <em style={{ borderColor: colors.accent || "#4c9c78" }} />
    </span>
  );
}
