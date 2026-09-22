import { useCallback, useEffect, useRef, useState } from "react";
import { pptApi, type PptGenerationJob } from "../api";

const TERMINAL = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);

export function usePptGeneration(options: { projectId?: string; pageCount: number; onComplete?: () => void | Promise<void> }) {
  const { projectId, pageCount, onComplete } = options;
  const projectRef = useRef(projectId);
  const onCompleteRef = useRef(onComplete);
  const sourceRef = useRef<EventSource | null>(null);
  const timerRef = useRef<number | null>(null);
  const jobRef = useRef<string | null>(null);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  projectRef.current = projectId;
  onCompleteRef.current = onComplete;

  const stop = useCallback(() => {
    if (timerRef.current) { window.clearInterval(timerRef.current); timerRef.current = null; }
    sourceRef.current?.close();
    sourceRef.current = null;
    jobRef.current = null;
    setRunning(false);
  }, []);

  const finish = useCallback(async (job: PptGenerationJob) => {
    if (job.status === "failed" || job.status === "cancelled") setError(job.error_message || "智能排版失败，请重试");
    if (job.status === "completed" || job.status === "completed_with_errors") {
      setProgress(100);
      await onCompleteRef.current?.();
    }
    stop();
  }, [stop]);

  const generate = useCallback(async () => {
    const id = projectRef.current;
    if (!id || running) return;
    stop();
    setError(null);
    setProgress(2);
    setRunning(true);
    let total = Math.max(1, pageCount);
    const source = new EventSource(pptApi.streamUrl(id));
    sourceRef.current = source;
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { event_type?: string; payload?: Record<string, unknown> };
        const body = payload.payload || {};
        if (body.job_id && jobRef.current && body.job_id !== jobRef.current) return;
        if (typeof body.total_pages === "number") total = body.total_pages;
        if (payload.event_type === "page.designed") {
          const completed = typeof body.completed_pages === "number" ? body.completed_pages : 0;
          setProgress((current) => Math.max(current, Math.min(96, Math.round((completed / total) * 100))));
        }
        if (payload.event_type === "planner.completed") setProgress((current) => Math.max(current, 15));
        if (payload.event_type === "generation.completed") { setProgress(100); void finish({ id: String(body.job_id || jobRef.current || ""), project_id: id, status: "completed", stage: "complete", total_pages: total, completed_pages: total, failed_pages: 0 }); }
        if (payload.event_type === "generation.failed") void finish({ id: String(body.job_id || jobRef.current || ""), project_id: id, status: "failed", stage: "failed", total_pages: total, completed_pages: 0, failed_pages: 1, error_message: typeof body.error === "string" ? body.error : "智能排版失败" });
      } catch { /* malformed events are ignored; polling remains authoritative */ }
    };
    try {
      const { data: job } = await pptApi.generateDesign(id);
      jobRef.current = job.id;
      timerRef.current = window.setInterval(() => {
        void pptApi.generationJob(id, job.id).then(({ data }) => {
          if (typeof data.total_pages === "number") total = data.total_pages;
          if (data.total_pages) setProgress(Math.max(2, Math.min(99, Math.round((data.completed_pages / data.total_pages) * 100))));
          if (TERMINAL.has(data.status)) void finish(data);
        }).catch(() => undefined);
      }, 3_000);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "智能排版失败，请重试");
      stop();
    }
  }, [finish, pageCount, running, stop]);

  useEffect(() => () => stop(), [projectId, stop]);
  return { running, progress, error, generate, cancel: stop };
}
