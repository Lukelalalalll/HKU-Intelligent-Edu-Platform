/**
 * Inline icon set for the courseware studio.
 *
 * A local SVG set keeps the UI crisp without shipping an icon dependency and
 * replaces the platform-dependent glyphs used by the previous chrome.
 */
import React from "react";

export type StudioIconName =
  | "back" | "next" | "down" | "check" | "sparkle" | "image" | "file" | "trash"
  | "more" | "search" | "download" | "play" | "close" | "refresh" | "grid"
  | "plus" | "send" | "stop" | "attach" | "pages" | "palette" | "wand" | "message"
  | "alert" | "lock" | "layout" | "text" | "edit";

const strokePaths: Partial<Record<StudioIconName, string[]>> = {
  back: ["M15 5l-7 7 7 7"],
  next: ["M9 5l7 7-7 7"],
  down: ["M6 9l6 6 6-6"],
  check: ["M4.5 12.5l5 5L20 6.5"],
  image: ["M4 5.5h16v13H4z", "M8.2 10.2a1.7 1.7 0 1 0 0.1 0z", "M4 16.5l4.6-4.6L14 17.3", "M12.8 14.6l2.4-2.4 4.8 4.8"],
  file: ["M14 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5z", "M14 3.5v5h5"],
  trash: ["M4.5 7h15", "M9.5 7V4.8h5V7", "M6.5 7l0.8 13h9.4l0.8-13", "M10 11v5.5", "M14 11v5.5"],
  search: ["M11 4.5a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13z", "M16 16l4 4"],
  download: ["M12 4v11", "M7.5 10.5L12 15l4.5-4.5", "M5 19.5h14"],
  close: ["M6 6l12 12", "M18 6L6 18"],
  refresh: ["M19.5 12a7.5 7.5 0 1 1-2.2-5.3", "M19.5 4.5V10H14"],
  grid: ["M4.5 4.5h6v6h-6z", "M13.5 4.5h6v6h-6z", "M4.5 13.5h6v6h-6z", "M13.5 13.5h6v6h-6z"],
  plus: ["M12 5v14", "M5 12h14"],
  send: ["M12 19V5", "M6 10.5L12 4.5l6 6"],
  stop: ["M7 7h10v10H7z"],
  attach: ["M20 11.5l-7.9 7.9a4.9 4.9 0 1 1-7-7l8.6-8.6a3.3 3.3 0 0 1 4.7 4.7l-8.6 8.6a1.7 1.7 0 0 1-2.4-2.4l7.7-7.7"],
  pages: ["M8 4.5h8.5L20 8v11.5H8z", "M16 4.5V8h3.5", "M4 8v11.5"],
  palette: ["M12 3.5a8.5 8.5 0 1 0 0 17c1.4 0 2-0.8 2-1.8s-0.7-1.6-0.7-2.4c0-1 0.8-1.7 1.8-1.7h1.6a3.8 3.8 0 0 0 3.8-3.8c0-4-4.1-7.3-8.5-7.3z", "M8 10.2a1.15 1.15 0 1 0 0.1 0z", "M11.6 7.6a1.15 1.15 0 1 0 0.1 0z", "M15.4 9.4a1.15 1.15 0 1 0 0.1 0z"],
  wand: ["M5 19L15.5 8.5", "M14 5l1.2 2.8L18 9l-2.8 1.2L14 13l-1.2-2.8L10 9l2.8-1.2z", "M18.5 14.5l0.6 1.4 1.4 0.6-1.4 0.6-0.6 1.4-0.6-1.4-1.4-0.6 1.4-0.6z"],
  message: ["M4.5 5.5h15v10h-9l-4 3.2v-3.2h-2z"],
  alert: ["M12 4.5l8.5 15h-17z", "M12 9.5v4.5", "M12 17v0.2"],
  lock: ["M6.5 10.5h11v9h-11z", "M8.8 10.5V8a3.2 3.2 0 0 1 6.4 0v2.5"],
  layout: ["M4.5 5.5h15v13h-15z", "M4.5 10h15", "M10 10v8.5"],
  text: ["M5 6h14", "M12 6v13"],
  edit: ["M4.5 19.5l0.5-4 10.6-10.6 3.5 3.5L8.5 19z", "M13.5 6.5l3.5 3.5"],
};

const fillPaths: Partial<Record<StudioIconName, string[]>> = {
  sparkle: ["M12 2.2l1.9 6.1 6.1 1.9-6.1 1.9L12 18.2l-1.9-6.1L4 10.2l6.1-1.9z", "M18.6 15.2l0.7 2 2 0.7-2 0.7-0.7 2-0.7-2-2-0.7 2-0.7z"],
  play: ["M8.5 5.5l10 6.5-10 6.5z"],
  more: ["M6 12a1.1 1.1 0 1 0 0.1 0z", "M12 12a1.1 1.1 0 1 0 0.1 0z", "M18 12a1.1 1.1 0 1 0 0.1 0z"],
};

export type StudioIconProps = {
  name: StudioIconName;
  size?: number;
  className?: string;
};

/** Render one studio icon. */
export function StudioIcon({ name, size = 18, className }: StudioIconProps) {
  const filled = fillPaths[name];
  const paths = filled ?? strokePaths[name] ?? [];
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      stroke={filled ? "none" : "currentColor"}
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths.map((path, index) => <path key={`${name}-${index}`} d={path} />)}
    </svg>
  );
}

export default StudioIcon;
