import { useCallback, useEffect, useRef, useState } from "react";
import type { PptDocument, PptPage } from "../api";

export type PendingSave = { projectId: string; pageId: string; document: PptDocument; revision: number };

export function usePptAutosave(options: {
  projectId?: string;
  save: (pending: PendingSave) => Promise<PptPage>;
  onSaved: (page: PptPage) => void;
  onError?: (error: unknown) => void;
  delayMs?: number;
}) {
  const { projectId, save, onSaved, onError, delayMs = 350 } = options;
  const projectIdRef = useRef(projectId);
  const saveRef = useRef(save);
  const onSavedRef = useRef(onSaved);
  const onErrorRef = useRef(onError);
  const delayRef = useRef(delayMs);
  projectIdRef.current = projectId;
  saveRef.current = save;
  onSavedRef.current = onSaved;
  onErrorRef.current = onError;
  delayRef.current = delayMs;
  const pendingRef = useRef<PendingSave | null>(null);
  const timerRef = useRef<number | null>(null);
  const [saving, setSaving] = useState(false);

  const flush = useCallback(async () => {
    if (timerRef.current) { window.clearTimeout(timerRef.current); timerRef.current = null; }
    const pending = pendingRef.current;
    if (!pending) return;
    pendingRef.current = null;
    setSaving(true);
    try { onSavedRef.current(await saveRef.current(pending)); }
    catch (error) { onErrorRef.current?.(error); }
    finally { setSaving(false); }
  }, []);

  const schedule = useCallback((page: PptPage, document: PptDocument) => {
    if (!projectIdRef.current) return;
    pendingRef.current = { projectId: projectIdRef.current, pageId: page.id, document, revision: page.document_revision || 1 };
    if (timerRef.current) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => { void flush(); }, delayRef.current);
  }, [flush]);

  useEffect(() => () => { void flush(); }, [flush, projectId]);
  return { saving, schedule, flush };
}
