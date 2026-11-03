/**
 * Visual research surface: page list, candidate images and selection state.
 */
import React, { useEffect, useRef, useState } from "react";
import { useI18n } from "../../i18n";
import AuthedImage from "../../shared/components/AuthedImage";
import { StudioIcon } from "./icons";
import type { StudioModel } from "./types";

export type VisualSurfaceProps = { model: StudioModel };
const MAX_SELECTION = 6;

/** Candidate image review. */
export default function VisualSurface({ model }: VisualSurfaceProps) {
  const { t } = useI18n();
  const { pages, visualRunning, actions } = model;
  const [index, setIndex] = useState(0);
  const [draft, setDraft] = useState<Record<string, string[]>>({});
  const [savingSelection, setSavingSelection] = useState(false);
  const autoStarted = useRef(false);
  const page = pages[Math.min(index, Math.max(0, pages.length - 1))];
  const assets = page?.asset_manifest || [];
  const selected = (draft[page?.id || ""] ?? page?.selected_asset_ids ?? []).filter((id) => assets.some((asset) => asset.id === id));
  const pageStatus = page?.visual_plan?.asset_status || page?.statuses?.visual || "empty";
  const pageSearching = pageStatus === "running" || (visualRunning && pageStatus !== "ready" && pageStatus !== "failed" && pageStatus !== "degraded");
  const ready = pages.filter((item) => {
    const status = item.statuses?.visual;
    const assetStatus = item.visual_plan?.asset_status;
    return status === "ready" || status === "degraded" || assetStatus === "ready" || (item.asset_manifest || []).length > 0;
  }).length;
  const progress = pages.length ? Math.round((ready / pages.length) * 100) : 0;

  useEffect(() => {
    if (!pages.length || visualRunning || autoStarted.current) return;
    const empty = pages.every((item) => !(item.asset_manifest || []).length);
    if (!empty) return;
    autoStarted.current = true;
    actions.runVisualResearch();
  }, [pages.length, visualRunning, actions]);

  useEffect(() => {
    if (index > pages.length - 1) setIndex(Math.max(0, pages.length - 1));
  }, [pages.length, index]);

  const toggle = (id: string) => {
    if (!page) return;
    setDraft((current) => {
      const active = current[page.id] ?? selected;
      const next = active.includes(id) ? active.filter((item) => item !== id) : active.length < MAX_SELECTION ? [...active, id] : active;
      return { ...current, [page.id]: next };
    });
  };

  const saveSelection = async () => {
    if (!page) return;
    setSavingSelection(true);
    try {
      await actions.saveVisualSelection(page, selected);
    } finally {
      setSavingSelection(false);
    }
  };

  const emptyMessage = () => {
    if (pageSearching) return t("coursewareAgent.visual.searching");
    if (pageStatus === "failed") return page?.visual_plan?.asset_error ? t("coursewareAgent.visual.searchFailedWithError", { error: page.visual_plan.asset_error }) : t("coursewareAgent.visual.searchFailedRetry");
    if (pageStatus === "degraded") return t("coursewareAgent.visual.degraded");
    return t("coursewareAgent.visual.noCandidates");
  };

  return (
    <div className="st-surface st-visual" data-testid="studio-surface-visual">
      <header className="st-surface-head">
        <div>
          <span className="st-eyebrow">03 · {t("coursewareAgent.workspace.steps.visuals")}</span>
          <h2>{t("coursewareAgent.visual.title")}</h2>
          <p>{t("coursewareAgent.visual.subtitle", { max: MAX_SELECTION })}</p>
        </div>
        <span className={`st-state-pill ${ready === pages.length && pages.length ? "is-ready" : ""}`}>
          <i aria-hidden="true" /> {t("coursewareAgent.visual.readyCount", { ready, total: pages.length })}
        </span>
      </header>

      <div className="st-surface-body st-visual-body">
        <div className={`st-progress-banner ${visualRunning ? "is-running" : ""}`}>
          <div className="st-progress-banner-head">
            <strong>{visualRunning ? t("coursewareAgent.visual.running") : progress >= 100 ? t("coursewareAgent.visual.ready") : progress > 0 ? t("coursewareAgent.visual.readyCount", { ready, total: pages.length }) : t("coursewareAgent.visual.waiting")}</strong>
            <span>{progress}%</span>
          </div>
          <div className="st-progress-track"><i style={{ width: `${progress}%` }} /></div>
        </div>

        <div className="st-visual-grid">
          <aside className="st-card st-visual-pages">
            <header className="st-card-mini-head">
              <strong>{t("coursewareAgent.visual.pagesTitle")}</strong>
              <span>{pages.length}</span>
            </header>
            <div className="st-visual-page-list">
              {pages.map((item, itemIndex) => {
                const count = (draft[item.id] ?? item.selected_asset_ids ?? []).length;
                const status = item.statuses?.visual;
                const total = (item.asset_manifest || []).length;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={itemIndex === index ? "is-active" : ""}
                    onClick={() => setIndex(itemIndex)}
                  >
                    <span className="st-visual-page-num">{String(itemIndex + 1).padStart(2, "0")}</span>
                    <span className="st-visual-page-text">
                      <b>{item.title}</b>
                      <small>{item.section_title || t("coursewareAgent.outline.untitledSection")}</small>
                    </span>
                    <span className={`st-visual-page-state ${status === "ready" ? "is-ready" : status === "failed" ? "is-failed" : ""}`}>
                      {total ? `${count}/${total}` : status === "running" ? "…" : "0"}
                    </span>
                  </button>
                );
              })}
            </div>
          </aside>

          <section className="st-card st-visual-assets">
            <header className="st-visual-toolbar">
              <div>
                <span className="st-eyebrow">{t("coursewareAgent.visual.pageLabel", { page: (page?.sort_order ?? index) + 1 })}</span>
                <strong>{page?.title}</strong>
              </div>
              <div className="st-visual-toolbar-actions">
                <span className="st-count">{t("coursewareAgent.visual.selectedCount", { selected: selected.length, max: MAX_SELECTION })}</span>
                <button type="button" className="st-mini-button" onClick={() => page && setDraft((current) => ({ ...current, [page.id]: assets.map((asset) => asset.id) }))} disabled={!page || !assets.length}>
                  {t("coursewareAgent.visual.selectAll")}
                </button>
                <button type="button" className="st-mini-button" onClick={() => page && setDraft((current) => ({ ...current, [page.id]: [] }))} disabled={!page || !selected.length}>
                  {t("coursewareAgent.visual.clearSelection")}
                </button>
                <button type="button" className="st-mini-button" onClick={() => void saveSelection()} disabled={!page || !assets.length || savingSelection}>
                  <StudioIcon name="check" size={13} /> {savingSelection ? t("coursewareAgent.workspace.saving") : t("coursewareAgent.visual.saveSelection")}
                </button>
                <button type="button" className="st-icon-button" onClick={actions.runVisualResearch} disabled={visualRunning} title={t("coursewareAgent.visual.regenerate")} aria-label={t("coursewareAgent.visual.regenerate")}>
                  <StudioIcon name="refresh" size={15} className={visualRunning ? "is-spinning" : undefined} />
                </button>
              </div>
            </header>

            {(page?.bullets || []).length ? (
              <ul className="st-visual-bullets">
                {(page?.bullets || []).map((bullet) => <li key={bullet}>{bullet}</li>)}
                {!(page?.bullets || []).length ? <li className="is-empty">{t("coursewareAgent.visual.noBullets")}</li> : null}
              </ul>
            ) : (
              <p className="st-muted">{t("coursewareAgent.visual.noBullets")}</p>
            )}

            {assets.length ? (
              <div className="st-asset-grid">
                {assets.map((asset) => {
                  const active = selected.includes(asset.id);
                  return (
                    <button key={asset.id} type="button" className={`st-asset ${active ? "is-selected" : ""}`} onClick={() => toggle(asset.id)} aria-pressed={active}>
                      <span className="st-asset-media">
                        <AuthedImage
                          src={asset.public_url || asset.src}
                          alt={asset.alt || page?.title || t("coursewareAgent.visual.untitledAsset")}
                          placeholder={<span className="st-asset-placeholder">{t("coursewareAgent.visual.noPreview")}</span>}
                        />
                        <span className="st-asset-check" aria-hidden="true">{active ? <StudioIcon name="check" size={13} /> : null}</span>
                      </span>
                      <span className="st-asset-title">{asset.title || t("coursewareAgent.visual.untitledAsset")}</span>
                      <small>{asset.license || t("coursewareAgent.visual.licenseRecorded")}{asset.score ? ` · ${Math.round(asset.score * 100)}%` : ""}</small>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="st-empty-block">
                <span aria-hidden="true"><StudioIcon name="image" size={22} /></span>
                <p>{emptyMessage()}</p>
              </div>
            )}
          </section>
        </div>
      </div>

      <footer className="st-surface-foot">
        <span className="st-foot-hint">
          {visualRunning ? t("coursewareAgent.visual.running") : t("coursewareAgent.visual.readyCount", { ready, total: pages.length })}
        </span>
        <div className="st-foot-actions">
          <button type="button" className="st-ghost-button" onClick={() => actions.navigate("outline")}>
            <StudioIcon name="back" size={14} /> {t("coursewareAgent.workspace.back")}
          </button>
          <button type="button" className="st-primary-button" onClick={() => actions.navigate("theme")} disabled={visualRunning || !pages.length}>
            {t("coursewareAgent.visual.continue")}
            <StudioIcon name="next" size={15} />
          </button>
        </div>
      </footer>
    </div>
  );
}
