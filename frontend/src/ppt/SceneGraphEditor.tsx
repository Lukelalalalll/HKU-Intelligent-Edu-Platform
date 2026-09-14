import React, { useEffect, useRef, useState } from "react";
import { fabric } from "fabric";
import type { PptDocument, PptEditorAsset, PptSlideElement, PptTextRun } from "../api";
import { SLIDE_HEIGHT, SLIDE_WIDTH, SlideRenderer, themeBackground } from "./SlideRenderer";

type Props = {
  document: PptDocument;
  editable?: boolean;
  onChange?: (document: PptDocument) => void;
  onUploadImage?: (file: File) => Promise<PptEditorAsset>;
};

type PptFabricObject = fabric.Object & { pptElement?: PptSlideElement; pptType?: string; assetId?: string; naturalWidth?: number; naturalHeight?: number; zIndex?: number; locked?: boolean };

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));
const pct = (value: number, total: number) => (value / total) * 100;
const objectSize = (object: PptFabricObject) => ({ width: (object.width || 0) * (object.scaleX || 1), height: (object.height || 0) * (object.scaleY || 1) });
const isText = (object: PptFabricObject | undefined) => Boolean(object && ["textbox", "i-text", "text"].includes(String(object.type)));

function applyRuns(object: fabric.IText, runs?: PptTextRun[]) {
  if (!runs?.length) return;
  for (const run of runs) {
    const styles: Record<string, unknown> = {};
    if (run.font_family) styles.fontFamily = run.font_family;
    if (run.font_size) styles.fontSize = run.font_size;
    if (run.font_weight) styles.fontWeight = run.font_weight;
    if (run.italic != null) styles.fontStyle = run.italic ? "italic" : "normal";
    if (run.underline != null) styles.underline = run.underline;
    if (run.strike != null) styles.linethrough = run.strike;
    if (run.color) styles.fill = run.color;
    if (run.highlight) styles.textBackgroundColor = run.highlight;
    if (Object.keys(styles).length) object.setSelectionStyles(styles, run.start, run.end);
  }
}

function runsFromObject(object: fabric.IText): PptTextRun[] | undefined {
  const styles = object.styles || {};
  const result: PptTextRun[] = [];
  let offset = 0;
  const lines = String(object.text || "").split("\n");
  lines.forEach((line, lineIndex) => {
    for (let index = 0; index < line.length; index += 1) {
      const style = (styles[lineIndex] || {})[index] || {};
      const previous = result[result.length - 1];
      const signature = JSON.stringify(style);
      const previousSignature = previous ? JSON.stringify({ font_family: previous.font_family, font_size: previous.font_size, font_weight: previous.font_weight, italic: previous.italic, underline: previous.underline, strike: previous.strike, color: previous.color, highlight: previous.highlight }) : "";
      const current: PptTextRun = { start: offset + index, end: offset + index + 1, font_family: style.fontFamily, font_size: style.fontSize, font_weight: style.fontWeight, italic: style.fontStyle === "italic", underline: Boolean(style.underline), strike: Boolean(style.linethrough), color: style.fill, highlight: style.textBackgroundColor };
      if (previous && signature === previousSignature && previous.end === current.start) previous.end = current.end;
      else result.push(current);
    }
    offset += line.length + (lineIndex < lines.length - 1 ? 1 : 0);
  });
  return result.length ? result : undefined;
}

function elementFromObject(object: PptFabricObject): PptSlideElement {
  const size = objectSize(object);
  const base: PptSlideElement = {
    id: object.pptElement?.id || `element-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    type: object.pptType || object.pptElement?.type || (isText(object) ? "text" : object.type === "image" ? "image" : "shape"),
    x: clamp(pct(object.left || 0, SLIDE_WIDTH), 0, 100),
    y: clamp(pct(object.top || 0, SLIDE_HEIGHT), 0, 100),
    w: clamp(pct(size.width, SLIDE_WIDTH), 0, 100),
    h: clamp(pct(size.height, SLIDE_HEIGHT), 0, 100),
    zIndex: object.pptElement?.zIndex || 1,
    rotation: object.angle || 0,
    opacity: object.opacity ?? 1,
    locked: object.pptElement?.locked,
    visible: object.visible !== false,
    name: object.pptElement?.name,
  };
  if (isText(object)) {
    const text = object as fabric.IText;
    return { ...base, text: text.text || "", font_size: Number(text.fontSize || 18), font_family: text.fontFamily, font_weight: text.fontWeight, color: String(text.fill || "#173f32"), align: (text.textAlign || "left") as PptSlideElement["align"], text_runs: runsFromObject(text), paragraph_style: { align: (text.textAlign || "left") as PptSlideElement["align"], line_height: text.lineHeight, letter_spacing: text.charSpacing } };
  }
  if (object.type === "image") {
    const image = object as PptFabricObject & fabric.Image;
    return { ...base, type: "image", src: image.getSrc(), asset_id: image.assetId, natural_width: image.naturalWidth, natural_height: image.naturalHeight, object_fit: image.pptElement?.object_fit || "contain", crop: image.pptElement?.crop, flip_x: image.flipX, flip_y: image.flipY, alt: image.pptElement?.alt };
  }
  return { ...base, type: object.pptType || "shape", fill: String(object.fill || "transparent"), stroke: object.stroke ? String(object.stroke) : undefined, stroke_width: Number(object.strokeWidth || 1), radius: Number((object as fabric.Rect).rx || 0), shape: object.pptElement?.shape };
}

function documentFromCanvas(canvas: fabric.Canvas): PptDocument {
  const elements = canvas.getObjects().filter((object) => object.visible !== false).sort((a, b) => ((a as PptFabricObject).zIndex || 0) - ((b as PptFabricObject).zIndex || 0)).map((object) => elementFromObject(object as PptFabricObject));
  return { version: 3, canvas: { width: SLIDE_WIDTH, height: SLIDE_HEIGHT }, elements };
}

function addElement(canvas: fabric.Canvas, element: PptSlideElement): Promise<PptFabricObject | null> {
  const x = (element.x / 100) * SLIDE_WIDTH; const y = (element.y / 100) * SLIDE_HEIGHT; const width = (element.w / 100) * SLIDE_WIDTH; const height = (element.h / 100) * SLIDE_HEIGHT;
  const common = { left: x, top: y, angle: element.rotation || 0, opacity: element.opacity ?? 1, selectable: !element.locked, evented: !element.locked, visible: element.visible !== false };
  if (element.type === "image" && element.src) {
    return new Promise((resolve) => {
      let settled = false;
      const finish = (value: PptFabricObject | null) => { if (settled) return; settled = true; resolve(value); };
      // A stale/deleted asset must never block the rest of the slide from
      // rendering. Keep a bounded timeout, but allow authenticated local
      // editor assets enough time to arrive on a cold development server.
      const timeout = window.setTimeout(() => finish(null), 10000);
      try {
        const source = String(element.src);
        // Editor assets are served by the authenticated API on the same
        // origin. Passing crossOrigin=anonymous for those URLs strips the
        // session credentials and makes Fabric receive a blank image. Only
        // opt into CORS for genuinely remote URLs.
        let imageOptions: { crossOrigin: "anonymous" } | undefined;
        try {
          const resolved = new URL(source, window.location.href);
          if (/^https?:$/.test(resolved.protocol) && resolved.origin !== window.location.origin) imageOptions = { crossOrigin: "anonymous" };
        } catch {
          imageOptions = undefined;
        }
        fabric.Image.fromURL(source, (image: fabric.Image, isError?: boolean) => {
          window.clearTimeout(timeout);
          if (isError || !image || !image.getElement?.()) return finish(null);
          image.set({ ...common, width: image.width || width, height: image.height || height, scaleX: width / (image.width || width), scaleY: height / (image.height || height), objectFit: element.object_fit, flipX: element.flip_x, flipY: element.flip_y, lockUniScale: element.lock_aspect_ratio !== false } as any);
          const target = image as PptFabricObject & fabric.Image;
          target.pptElement = element; target.pptType = "image"; target.assetId = element.asset_id;
          target.naturalWidth = element.natural_width || image.width || width; target.naturalHeight = element.natural_height || image.height || height;
          canvas.add(image); finish(target);
        }, imageOptions);
      } catch {
        window.clearTimeout(timeout);
        finish(null);
      }
    });
  }
  if (["shape", "rect", "rectangle", "rounded-rectangle", "circle", "oval"].includes(String(element.type))) {
    const shape = String(element.type) === "circle" || String(element.shape) === "circle" ? new fabric.Circle({ ...common, radius: Math.min(width, height) / 2, fill: element.fill || "#dceee4", stroke: element.stroke, strokeWidth: element.stroke_width || 1 }) : new fabric.Rect({ ...common, width, height, rx: element.radius || (String(element.type).includes("rounded") ? 18 : 0), ry: element.radius || (String(element.type).includes("rounded") ? 18 : 0), fill: element.fill || element.background || "#dceee4", stroke: element.stroke, strokeWidth: element.stroke_width || 1 });
    (shape as PptFabricObject).pptElement = element; (shape as PptFabricObject).pptType = "shape"; canvas.add(shape); return Promise.resolve(shape as PptFabricObject);
  }
  const text = new fabric.Textbox(element.text || (element.items || []).join("\n"), { ...common, width, height, fontSize: element.font_size || 18, fontFamily: element.font_family || "Arial", fontWeight: element.font_weight || 500, fill: element.color || "#173f32", textAlign: element.align || element.paragraph_style?.align || "left", lineHeight: element.paragraph_style?.line_height || 1.3, charSpacing: element.paragraph_style?.letter_spacing || 0, editable: true, padding: 4 });
  applyRuns(text, element.text_runs); (text as PptFabricObject).pptElement = element; (text as PptFabricObject).pptType = element.type || "text"; canvas.add(text); return Promise.resolve(text as PptFabricObject);
}

export default function SceneGraphEditor({ document, editable = true, onChange, onUploadImage }: Props) {
  const canvasElement = useRef<HTMLCanvasElement | null>(null); const host = useRef<HTMLDivElement | null>(null); const stage = useRef<HTMLDivElement | null>(null); const canvasRef = useRef<fabric.Canvas | null>(null); const hydrating = useRef(false); const renderId = useRef(0); const initialized = useRef(false); const history = useRef<PptDocument[]>([]); const future = useRef<PptDocument[]>([]); const beforeChange = useRef<PptDocument | null>(null); const [selected, setSelected] = useState<PptFabricObject[]>([]); const [editing, setEditing] = useState(false); const [zoom, setZoom] = useState(0.8); const zoomRef = useRef(0.8); const [showGrid, setShowGrid] = useState(false); const [fallbackVisible, setFallbackVisible] = useState(false); const [liveDocument, setLiveDocument] = useState(document); const fileRef = useRef<HTMLInputElement | null>(null);
  const propertiesCollapsed = selected.length === 0;
  const active = selected[0]; const textActive = isText(active); const imageActive = active?.type === "image";
  const emit = () => { const canvas = canvasRef.current; if (!canvas || hydrating.current) return; const next = { ...documentFromCanvas(canvas), theme: document.theme, layout: document.layout, speaker_notes: document.speaker_notes }; setLiveDocument(next); onChange?.(next); };
  const snapshot = () => { const canvas = canvasRef.current; if (!canvas || hydrating.current) return; history.current = [...history.current.slice(-39), documentFromCanvas(canvas)]; future.current = []; beforeChange.current = null; };
  const fitCanvas = () => {
    const canvas = canvasRef.current; const hostNode = host.current; const stageNode = stage.current;
    if (!canvas || !hostNode || !stageNode) return;
    const availableWidth = Math.max(240, hostNode.clientWidth - 24);
    const availableHeight = Math.max(160, hostNode.clientHeight - 24);
    const fit = Math.min(availableWidth / SLIDE_WIDTH, availableHeight / SLIDE_HEIGHT);
    // The slider is a multiplier on the available fit size. The compact 40%
    // default keeps the surrounding editing controls and properties visible.
    const scale = Math.max(0.2, Math.min(zoomRef.current * fit, 1.35));
    const displayWidth = SLIDE_WIDTH * scale;
    const displayHeight = SLIDE_HEIGHT * scale;
    stageNode.style.width = `${displayWidth}px`;
    stageNode.style.height = `${displayHeight}px`;
    stageNode.style.setProperty("--ppt-stage-scale", String(scale));
    // Keep an intentionally enlarged slide reachable from the top-left when
    // it is larger than the viewport; centering an overflowing flex child can
    // otherwise hide its leading edge at scrollLeft = 0.
    hostNode.style.justifyContent = displayWidth > availableWidth ? "flex-start" : "center";
    hostNode.style.alignItems = displayHeight > availableHeight ? "flex-start" : "center";

    // Keep slide objects in their 1280×720 logical coordinate system while
    // using the fitted display size for both the CSS box and the retina
    // backing store. Fabric's viewport transform maps the logical slide into
    // that display box, and setDimensions initializes the backing store at
    // display pixels × devicePixelRatio.
    canvas.setZoom(scale);
    canvas.setDimensions({ width: displayWidth, height: displayHeight }, { backstoreOnly: true });
    canvas.setDimensions({ width: displayWidth, height: displayHeight }, { cssOnly: true });
    canvas.calcOffset();
    canvas.requestRenderAll();
  };
  const render = async (next: PptDocument) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const currentRender = ++renderId.current;
    hydrating.current = true;
    setLiveDocument(next);
    // Fabric's transparent canvas sits above this stage. Keep the stage itself
    // in sync with the document theme so the editable view has the same
    // background as the thumbnail/DOM renderer once Fabric takes over.
    if (stage.current) stage.current.style.background = themeBackground(next);
    stage.current?.classList.remove("fabric-ready");
    // Keep the read-only renderer available while Fabric is hydrating. This is
    // especially important for image-only slides, where Fabric may need to
    // wait for a remote asset before it has anything to paint.
    canvas.clear();
    // The read-only renderer is the visual safety net underneath Fabric. A
    // transparent Fabric background lets the slide remain visible while the
    // scene graph is rebuilding or while a browser canvas is recovering.
    canvas.backgroundColor = "transparent";
    try {
      // Text and shapes are synchronous. Add them immediately so a broken or
      // slow image URL can never blank the whole editor. Images settle in the
      // background and trigger a repaint when they become available.
      for (const element of next.elements || []) {
        if (currentRender !== renderId.current || canvasRef.current !== canvas) return;
        const task = addElement(canvas, element).catch(() => null);
        if (element.type === "image") task.then(() => {
          if (currentRender !== renderId.current || canvasRef.current !== canvas) return;
          canvas.requestRenderAll();
          if (canvas.getObjects().length > 0) {
            stage.current?.classList.add("fabric-ready");
            setFallbackVisible(false);
          }
        });
        else await task;
      }
    } finally {
      if (currentRender === renderId.current && canvasRef.current === canvas) {
        canvas.calcOffset();
        canvas.renderAll();
        setLiveDocument(next);
        // Keep the DOM renderer only until Fabric has painted at least one
        // object. This prevents the fallback and editable scene from creating
        // a visible double image while still covering failed/slow loads.
        const fabricReady = canvas.getObjects().length > 0;
        stage.current?.classList.toggle("fabric-ready", fabricReady);
        setFallbackVisible(Boolean(next.elements?.length) && !fabricReady);
        hydrating.current = false;
      }
    }
  };
  useEffect(() => { if (!canvasElement.current) return; const canvas = new fabric.Canvas(canvasElement.current, { width: SLIDE_WIDTH, height: SLIDE_HEIGHT, preserveObjectStacking: true, selection: true, uniformScaling: true, stopContextMenu: true }); canvasRef.current = canvas; const syncSelection = () => setSelected((canvas.getActiveObjects() as PptFabricObject[]) || []); const before = () => { beforeChange.current = documentFromCanvas(canvas); }; const modified = () => { if (beforeChange.current) { history.current = [...history.current.slice(-39), beforeChange.current]; future.current = []; beforeChange.current = null; } emit(); }; const textChanged = () => { if (!beforeChange.current) beforeChange.current = documentFromCanvas(canvas); emit(); }; canvas.on("selection:created", syncSelection); canvas.on("selection:updated", syncSelection); canvas.on("selection:cleared", () => setSelected([])); canvas.on("before:object:modified", before); canvas.on("object:modified", modified); canvas.on("text:changed", textChanged); canvas.on("text:editing:entered", () => setEditing(true)); canvas.on("text:editing:exited", () => { setEditing(false); modified(); }); initialized.current = true; void render(document).then(() => requestAnimationFrame(fitCanvas)); const resize = new ResizeObserver(() => fitCanvas()); if (host.current) resize.observe(host.current); requestAnimationFrame(fitCanvas); return () => { resize.disconnect(); renderId.current += 1; initialized.current = false; canvas.dispose(); canvasRef.current = null; }; }, []);
  useEffect(() => { if (initialized.current && canvasRef.current && !editing) void render(document); }, [document, editing]);
  useEffect(() => { zoomRef.current = zoom; fitCanvas(); }, [zoom]);
  useEffect(() => { const onKey = (event: KeyboardEvent) => { const canvas = canvasRef.current; if (!canvas || !editable) return; const target = event.target as HTMLElement; if (target.closest("input,select,textarea")) return; const key = event.key.toLowerCase(); if ((event.ctrlKey || event.metaKey) && key === "z") { event.preventDefault(); undo(); } else if ((event.ctrlKey || event.metaKey) && key === "y") { event.preventDefault(); redo(); } else if (key === "delete" || key === "backspace") { if (editing) return; event.preventDefault(); snapshot(); canvas.getActiveObjects().forEach((object) => canvas.remove(object)); canvas.discardActiveObject(); canvas.renderAll(); emit(); } else if (event.key.startsWith("Arrow") && selected.length) { event.preventDefault(); const step = event.shiftKey ? 10 : 1; selected.forEach((object) => { object.set({ left: (object.left || 0) + (event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0), top: (object.top || 0) + (event.key === "ArrowDown" ? step : event.key === "ArrowUp" ? -step : 0) }); object.setCoords(); }); canvas.renderAll(); emit(); } }; window.addEventListener("keydown", onKey); return () => window.removeEventListener("keydown", onKey); });
  const updateObject = (patch: Record<string, unknown>, record = true) => { const canvas = canvasRef.current; if (!canvas || !active) return; if (record) snapshot(); active.set(patch as any); active.setCoords(); canvas.renderAll(); emit(); setSelected([...canvas.getActiveObjects()] as PptFabricObject[]); };
  const applyText = (patch: Record<string, unknown>) => { if (!active || !textActive) return; const text = active as fabric.IText; snapshot(); if (text.isEditing && text.selectionStart !== text.selectionEnd) text.setSelectionStyles(patch, text.selectionStart, text.selectionEnd); else text.set(patch as any); canvasRef.current?.renderAll(); emit(); };
  const insertText = () => { const canvas = canvasRef.current; if (!canvas) return; snapshot(); const object = new fabric.Textbox("双击编辑文字", { left: 120, top: 120, width: 360, fontSize: 28, fill: "#173f32", fontFamily: "Arial", fontWeight: 600, editable: true, padding: 4 }) as fabric.Textbox & PptFabricObject; object.pptType = "text"; object.pptElement = { id: `text-${Date.now()}`, type: "text", x: 0, y: 0, w: 0, h: 0 }; canvas.add(object); canvas.setActiveObject(object); object.enterEditing(); canvas.renderAll(); emit(); };
  const insertShape = () => { const canvas = canvasRef.current; if (!canvas) return; snapshot(); const object = new fabric.Rect({ left: 160, top: 160, width: 260, height: 120, rx: 18, ry: 18, fill: "#dceee4", stroke: "#4b9a76", strokeWidth: 2 }) as PptFabricObject; object.pptType = "shape"; object.pptElement = { id: `shape-${Date.now()}`, type: "shape", x: 0, y: 0, w: 0, h: 0 }; canvas.add(object); canvas.setActiveObject(object); canvas.renderAll(); emit(); };
  const insertImage = async (file: File) => { if (!onUploadImage) return; const asset = await onUploadImage(file); const canvas = canvasRef.current; if (!canvas) return; snapshot(); const current = imageActive && active ? elementFromObject(active) : null; const previous = active; const element: PptSlideElement = { id: current?.id || `image-${Date.now()}`, type: "image", x: current?.x ?? 56, y: current?.y ?? 24, w: current?.w ?? 34, h: current?.h ?? 42, rotation: current?.rotation, src: asset.url, asset_id: asset.id, natural_width: asset.width, natural_height: asset.height, object_fit: current?.object_fit || "contain", crop: current?.crop, alt: asset.alt || asset.name, lock_aspect_ratio: current?.lock_aspect_ratio !== false }; const inserted = await addElement(canvas, element); if (!inserted) return; if (previous) canvas.remove(previous); canvas.setActiveObject(inserted); canvas.requestRenderAll(); emit(); };
  const undo = () => { const next = history.current.pop(); const canvas = canvasRef.current; if (!next || !canvas) return; future.current = [documentFromCanvas(canvas), ...future.current]; void render(next); onChange?.(next); };
  const redo = () => { const next = future.current.shift(); const canvas = canvasRef.current; if (!next || !canvas) return; history.current = [...history.current, documentFromCanvas(canvas)]; void render(next); onChange?.(next); };
  const align = (mode: "left" | "center" | "right" | "top" | "middle" | "bottom") => { const canvas = canvasRef.current; if (!canvas || !selected.length) return; snapshot(); const objects = selected; const bounds = objects.reduce((acc, object) => { const size = objectSize(object); return { left: Math.min(acc.left, object.left || 0), top: Math.min(acc.top, object.top || 0), right: Math.max(acc.right, (object.left || 0) + size.width), bottom: Math.max(acc.bottom, (object.top || 0) + size.height) }; }, { left: Infinity, top: Infinity, right: -Infinity, bottom: -Infinity }); objects.forEach((object) => { const size = objectSize(object); const left = mode === "left" ? bounds.left : mode === "center" ? (bounds.left + bounds.right - size.width) / 2 : mode === "right" ? bounds.right - size.width : object.left || 0; const top = mode === "top" ? bounds.top : mode === "middle" ? (bounds.top + bounds.bottom - size.height) / 2 : mode === "bottom" ? bounds.bottom - size.height : object.top || 0; object.set({ left, top }); object.setCoords(); }); canvas.renderAll(); emit(); };
  const bring = (direction: "front" | "back") => { const canvas = canvasRef.current; if (!canvas || !active) return; snapshot(); direction === "front" ? canvas.bringToFront(active) : canvas.sendToBack(active); canvas.renderAll(); emit(); };
  const duplicate = () => { const canvas = canvasRef.current; if (!canvas || !active) return; snapshot(); active.clone((clone: fabric.Object) => { const copied = clone as PptFabricObject; copied.set({ left: (active.left || 0) + 24, top: (active.top || 0) + 24 }); copied.pptElement = { ...(active.pptElement || elementFromObject(active)), id: `copy-${Date.now()}` }; canvas.add(copied); canvas.setActiveObject(copied); canvas.renderAll(); emit(); }); };
  const props = active ? elementFromObject(active) : null;
  return <div className="ppt-scene-editor">
    <div className="ppt-scene-toolbar" role="toolbar" aria-label="PowerPoint 编辑工具栏">
      <div className="ppt-scene-tool-group"><button onClick={undo} disabled={!history.current.length} title="撤销">↶</button><button onClick={redo} disabled={!future.current.length} title="重做">↷</button></div>
      <div className="ppt-scene-tool-group"><button onClick={insertText}>T 文本框</button><button onClick={() => fileRef.current?.click()}>▧ 图片</button><button onClick={insertShape}>▱ 形状</button></div>
      {textActive && <div className="ppt-scene-tool-group ppt-text-tools"><select value={String((active as fabric.IText).fontFamily || "Arial")} onChange={(event) => applyText({ fontFamily: event.target.value })}><option>Arial</option><option>Microsoft YaHei</option><option>PingFang SC</option><option>Georgia</option><option>Courier New</option></select><input aria-label="字号" type="number" min="6" max="180" value={Number((active as fabric.IText).fontSize || 18)} onChange={(event) => applyText({ fontSize: clamp(Number(event.target.value) || 18, 6, 180) })} /><button className={String((active as fabric.IText).fontWeight) === "700" || Number((active as fabric.IText).fontWeight) >= 600 ? "active" : ""} onClick={() => applyText({ fontWeight: Number((active as fabric.IText).fontWeight) >= 600 ? 400 : 700 })}>B</button><button className={(active as fabric.IText).fontStyle === "italic" ? "active" : ""} onClick={() => applyText({ fontStyle: (active as fabric.IText).fontStyle === "italic" ? "normal" : "italic" })}>I</button><button className={(active as fabric.IText).underline ? "active" : ""} onClick={() => applyText({ underline: !(active as fabric.IText).underline })}>U</button><label className="ppt-color-control" title="文字颜色"><span>A</span><input type="color" value={String((active as fabric.IText).fill || "#173f32").startsWith("#") ? String((active as fabric.IText).fill) : "#173f32"} onChange={(event) => applyText({ fill: event.target.value })} /></label><button onClick={() => applyText({ textAlign: "left" })}>≡</button><button onClick={() => applyText({ textAlign: "center" })}>≣</button><button onClick={() => applyText({ textAlign: "right" })}>≡</button></div>}
      {imageActive && <div className="ppt-scene-tool-group"><button onClick={() => updateObject({ flipX: !active.flipX })}>↔ 翻转</button><button onClick={() => updateObject({ flipY: !active.flipY })}>↕ 翻转</button><select value={String((active.pptElement?.object_fit || "contain"))} onChange={(event) => updateObject({ objectFit: event.target.value })}><option value="contain">完整显示</option><option value="cover">填充裁剪</option></select></div>}
      {selected.length > 0 && <div className="ppt-scene-tool-group"><button onClick={() => align("left")}>左对齐</button><button onClick={() => align("middle")}>垂直居中</button><button onClick={() => align("top")}>顶对齐</button><button onClick={duplicate}>复制</button><button onClick={() => bring("front")}>置顶</button><button onClick={() => bring("back")}>置底</button></div>}
      <div className="ppt-scene-tool-group ppt-scene-toolbar-end"><button className={showGrid ? "active" : ""} onClick={() => setShowGrid((value) => !value)}>网格</button><label>缩放 <input type="range" min="0.4" max="1.35" step="0.05" value={zoom} onChange={(event) => setZoom(Number(event.target.value))} /></label></div>
      <input ref={fileRef} hidden type="file" accept="image/*" onChange={(event) => { const file = event.target.files?.[0]; if (file) void insertImage(file); event.currentTarget.value = ""; }} />
    </div>
    <div className={`ppt-scene-workspace ${showGrid ? "show-grid" : ""} ${propertiesCollapsed ? "is-properties-collapsed" : ""}`}>
       <div className="ppt-scene-canvas-wrap" ref={host} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); const file = event.dataTransfer.files?.[0]; if (file?.type.startsWith("image/")) void insertImage(file); }}>
         <div className="ppt-scene-stage" ref={stage}>
           <div className={`ppt-scene-fallback ${fallbackVisible ? "visible" : ""}`} aria-hidden="true"><SlideRenderer document={liveDocument.elements?.length ? liveDocument : document} /></div>
           <canvas ref={canvasElement} aria-label="幻灯片画布" />
         </div>
       </div>
       <aside id="ppt-scene-properties-panel" className={`ppt-scene-properties ${propertiesCollapsed ? "is-collapsed" : ""}`} aria-hidden={propertiesCollapsed}><div className="ppt-scene-properties-head"><strong>格式</strong><span>{selected.length} 个对象</span></div>{props && <><label>名称<input value={props.name || ""} onChange={(event) => updateObject({ pptElement: { ...(active.pptElement || {}), name: event.target.value } })} /></label><div className="ppt-prop-grid"><label>X<input type="number" value={Number(props.x.toFixed(1))} onChange={(event) => updateObject({ left: (Number(event.target.value) / 100) * SLIDE_WIDTH })} /></label><label>Y<input type="number" value={Number(props.y.toFixed(1))} onChange={(event) => updateObject({ top: (Number(event.target.value) / 100) * SLIDE_HEIGHT })} /></label><label>宽<input type="number" value={Number(props.w.toFixed(1))} onChange={(event) => updateObject({ scaleX: ((Number(event.target.value) / 100) * SLIDE_WIDTH) / (active.width || 1) })} /></label><label>高<input type="number" value={Number(props.h.toFixed(1))} onChange={(event) => updateObject({ scaleY: ((Number(event.target.value) / 100) * SLIDE_HEIGHT) / (active.height || 1) })} /></label></div><label>旋转<input type="number" value={Math.round(props.rotation || 0)} onChange={(event) => updateObject({ angle: Number(event.target.value) })} /></label><label>透明度<input type="range" min="0" max="1" step="0.05" value={Number(props.opacity ?? 1)} onChange={(event) => updateObject({ opacity: Number(event.target.value) })} /></label><label className="ppt-checkbox"><input type="checkbox" checked={Boolean(active.locked)} onChange={(event) => { active.set({ selectable: !event.target.checked, evented: !event.target.checked }); updateObject({ pptElement: { ...(active.pptElement || {}), locked: event.target.checked } }); }} /> 锁定对象</label>{imageActive && <label>替代文字<input value={props.alt || ""} onChange={(event) => updateObject({ pptElement: { ...(active.pptElement || {}), alt: event.target.value } })} /></label>}</>}</aside>
    </div>
    <div className="ppt-scene-status">双击文字编辑 · 拖拽对象移动 · 角点保持比例缩放 · 方向键微调 · 当前画布 {SLIDE_WIDTH} × {SLIDE_HEIGHT}</div>
  </div>;
}
