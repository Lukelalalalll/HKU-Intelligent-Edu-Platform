/**
 * Full-screen presentation preview.
 */
import React, { useEffect, useRef, useState } from "react";
import type { PptPage } from "../../api";
import { useI18n } from "../../i18n";
import { SLIDE_HEIGHT, SLIDE_WIDTH, SlideRenderer, editableDocument } from "../SlideRenderer";
import { StudioIcon } from "./icons";

export type PresentSurfaceProps = {
  pages: PptPage[];
  index: number;
  onIndexChange: (index: number) => void;
  onClose: () => void;
};

/** Minimal, keyboard-driven presentation mode. */
export default function PresentSurface({ pages, index, onIndexChange, onClose }: PresentSurfaceProps) {
  const { t } = useI18n();
  const stageRef = useRef<HTMLDivElement | null>(null);
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const [scale, setScale] = useState(0.5);
  const page = pages[index] || pages[0];

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const update = () => {
      const availableWidth = Math.max(0, stage.clientWidth - 120);
      const availableHeight = Math.max(0, stage.clientHeight - 8);
      setScale(Math.min(1, availableWidth / SLIDE_WIDTH, availableHeight / SLIDE_HEIGHT));
    };
    const observer = new ResizeObserver(update);
    observer.observe(stage);
    update();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
      if (event.key === "ArrowLeft") onIndexChange(Math.max(0, index - 1));
      if (event.key === "ArrowRight") onIndexChange(Math.min(pages.length - 1, index + 1));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [index, onClose, onIndexChange, pages.length]);

  if (!page) return null;

  return (
    <div className="st-present" role="dialog" aria-modal="true" aria-label={t("coursewareAgent.present.previewTitle")} data-testid="studio-surface-present">
      <header className="st-present-head">
        <div>
          <span>{t("coursewareAgent.present.previewTitle")}</span>
          <strong>{page.title}</strong>
        </div>
        <div className="st-present-head-actions">
          <span className="st-present-count">{t("coursewareAgent.present.pageOf", { current: index + 1, total: pages.length })}</span>
          <button ref={closeRef} type="button" className="st-present-close" onClick={onClose} aria-label={t("coursewareAgent.present.exit")} title={t("coursewareAgent.present.exit")}>
            <StudioIcon name="close" size={17} />
          </button>
        </div>
      </header>

      <div className="st-present-stage" ref={stageRef}>
        <button type="button" className="st-present-nav" disabled={index === 0} onClick={() => onIndexChange(Math.max(0, index - 1))} aria-label={t("coursewareAgent.present.previous")}>
          <StudioIcon name="back" size={18} />
        </button>
        <div className="st-present-slide" style={{ width: SLIDE_WIDTH * scale, height: SLIDE_HEIGHT * scale }}>
          <div className="st-present-scale" style={{ width: SLIDE_WIDTH, height: SLIDE_HEIGHT, transform: `scale(${scale})` }}>
            <SlideRenderer document={editableDocument(page)} />
          </div>
        </div>
        <button type="button" className="st-present-nav" disabled={index === pages.length - 1} onClick={() => onIndexChange(Math.min(pages.length - 1, index + 1))} aria-label={t("coursewareAgent.present.next")}>
          <StudioIcon name="next" size={18} />
        </button>
      </div>

      <footer className="st-present-foot">
        <div className="st-present-dots" aria-hidden="true">
          {pages.map((item, itemIndex) => <i key={item.id} className={itemIndex === index ? "is-active" : itemIndex < index ? "is-past" : ""} />)}
        </div>
        <span>{t("coursewareAgent.present.hint")}</span>
      </footer>
    </div>
  );
}
