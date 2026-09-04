import React, { useEffect, useRef, useState } from "react";
import type { PptDocument, PptPage, PptSlideElement } from "../api";

export const SLIDE_WIDTH = 1280;
export const SLIDE_HEIGHT = 720;

const themeBackground = (document?: PptDocument | null) =>
  String(document?.theme?.background || document?.theme?.bg || "linear-gradient(135deg,#fbfefc,#eaf7ef)");

export const defaultDocument = (page: PptPage): PptDocument => {
  const theme = page.document?.theme || {};
  const bodyColor = String(theme.body || "#21463a");
  return {
    version: 2,
    canvas: { width: SLIDE_WIDTH, height: SLIDE_HEIGHT },
    layout: page.document?.layout || "title-content",
    theme: { ...theme, background: themeBackground(page.document) },
    elements: [
      { id: "title", type: "title", x: 7, y: 8, w: 86, h: 14, text: page.title || "未命名页面", font_size: 34, color: String(theme.title || "#0b6248"), font_weight: 800 },
      ...page.bullets.slice(0, 6).map((text, index) => ({
        id: `bullet-${index}`,
        type: "body",
        x: 9,
        y: 30 + index * 10,
        w: 80,
        h: 8,
        text: `• ${text}`,
        font_size: 19,
        color: bodyColor,
      })),
    ],
  };
};

export const editableDocument = (page: PptPage): PptDocument =>
  page.document?.elements?.length ? page.document : defaultDocument(page);

export type SlideRendererProps = {
  document: PptDocument;
  selectedId?: string | null;
  editable?: boolean;
  className?: string;
  onSelect?: (element: PptSlideElement) => void;
  onBackgroundPointerDown?: () => void;
  onPointerDown?: (event: React.PointerEvent<HTMLDivElement>, element: PptSlideElement) => void;
  onTextBlur?: (element: PptSlideElement, text: string) => void;
  onResizeStart?: (event: React.PointerEvent<HTMLButtonElement>, element: PptSlideElement) => void;
};

const elementText = (element: PptSlideElement) => element.text || (element.items || []).join("\n");

export function SlideRenderer({
  document,
  selectedId = null,
  editable = false,
  className = "",
  onSelect,
  onBackgroundPointerDown,
  onPointerDown,
  onTextBlur,
  onResizeStart,
}: SlideRendererProps) {
  return (
    <div className={`ppt-slide-renderer ${className}`} style={{ background: themeBackground(document) }} onPointerDown={() => onBackgroundPointerDown?.()}>
      {document.elements.map((element) => {
        const type = String(element.type || "body").toLowerCase();
        const raw = element as PptSlideElement & Record<string, any>;
        const shapeTypes = new Set(["shape", "rect", "rectangle", "rounded-rectangle", "rounded_rectangle", "roundrect", "card", "panel", "box", "bar", "divider", "line", "rule", "circle", "oval", "ellipse", "background", "decoration"]);
        const isImage = type === "image" || (type === "icon" && Boolean(element.src));
        const isShape = shapeTypes.has(type) || (!elementText(element) && ["fill", "fill_color", "background", "background_color", "stroke", "stroke_color", "shape"].some((key) => raw[key] != null && raw[key] !== ""));
        const shapeHint = String(raw.shape || "").toLowerCase().replace("_", "-");
        const text = elementText(element);
        const style: React.CSSProperties = {
          left: `${element.x}%`,
          top: `${element.y}%`,
          width: `${element.w}%`,
          height: `${element.h}%`,
          zIndex: element.zIndex || 1,
          color: element.color || "#173f32",
          fontSize: `${element.font_size || 18}px`,
          fontFamily: element.font_family || "Arial, sans-serif",
          fontWeight: element.font_weight || (type === "title" ? 800 : 500),
          textAlign: element.align || "left",
          opacity: element.opacity ?? 1,
          borderRadius: (type === "circle" || type === "oval" || type === "ellipse" || ["circle", "oval", "ellipse"].includes(shapeHint)) ? "50%" : element.radius ? `${element.radius}px` : undefined,
          background: raw.fill || raw.fill_color || raw.background || raw.background_color || "transparent",
          border: raw.stroke || raw.stroke_color || raw.border_color ? `${raw.stroke_width || raw.line_width || 1}px solid ${raw.stroke || raw.stroke_color || raw.border_color}` : undefined,
          objectFit: element.object_fit || "cover",
        };
        return (
          <div
            key={element.id}
            className={`ppt-slide-element ppt-slide-element-${type} ${selectedId === element.id ? "selected" : ""} ${isImage ? "is-image" : ""}`}
            style={style}
            onClick={() => editable && onSelect?.(element)}
            onPointerDown={(event) => {
              if (!editable || element.locked) return;
              event.stopPropagation();
              onSelect?.(element);
              onPointerDown?.(event, element);
            }}
            contentEditable={editable && selectedId === element.id && !isShape && !isImage}
            suppressContentEditableWarning
            onBlur={(event) => {
              if (editable && !isShape && !isImage) onTextBlur?.(element, event.currentTarget.textContent || "");
            }}
          >
            {isImage && element.src ? <img src={element.src} alt={element.alt || "课件图片"} draggable={false} /> : isImage ? <span className="ppt-slide-image-placeholder">图片</span> : isShape ? null : text}
            {editable && selectedId === element.id && onResizeStart ? (
              <button className="ppt-resize-handle" type="button" aria-label="调整大小" onPointerDown={(event) => onResizeStart(event, element)} />
            ) : null}
          </div>
        );
      })}
      {!document.elements.length && <div className="ppt-slide-empty">等待 Agent 生成设计稿</div>}
    </div>
  );
}

export function SlideThumbnail({ page, selected, onClick }: { page: PptPage; selected: boolean; onClick: () => void }) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(0.15);
  useEffect(() => {
    const node = viewportRef.current;
    if (!node) return;
    const observer = new ResizeObserver(() => setScale(Math.max(0.05, node.clientWidth / SLIDE_WIDTH)));
    observer.observe(node);
    setScale(Math.max(0.05, node.clientWidth / SLIDE_WIDTH));
    return () => observer.disconnect();
  }, []);
  return (
    <button className={`ppt-thumbnail-card ${selected ? "active" : ""}`} onClick={onClick} type="button">
      <span className="ppt-thumbnail-number">{String(page.sort_order + 1).padStart(2, "0")}</span>
      <div className="ppt-thumbnail-viewport" ref={viewportRef}>
        <div className="ppt-thumbnail-scale" style={{ width: SLIDE_WIDTH, height: SLIDE_HEIGHT, transform: `scale(${scale})` }}><SlideRenderer document={editableDocument(page)} /></div>
      </div>
      <strong title={page.title}>{page.title || "未命名页面"}</strong>
    </button>
  );
}
