import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PptDocument } from "../api";
import { SlideRenderer } from "./SlideRenderer";

describe("SlideRenderer resize control", () => {
  it("does not put a Unicode arrow into the preview DOM", () => {
    const document: PptDocument = {
      version: 2,
      canvas: { width: 1280, height: 720 },
      elements: [{ id: "title", type: "title", x: 5, y: 5, w: 40, h: 12, text: "标题" }],
    };
    const markup = renderToStaticMarkup(
      <SlideRenderer document={document} editable selectedId="title" onResizeStart={() => undefined} />,
    );

    expect(markup).not.toContain(String.fromCodePoint(0x2198));
    expect(markup).toContain('aria-label="调整大小"');
  });
});
