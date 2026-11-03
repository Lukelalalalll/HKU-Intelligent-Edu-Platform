import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { getApiErrorMessage, teacherVideoApi } from "../../../api";
import { useI18n, type TranslationKey, type Translator } from "../../../i18n";
import { queryKeys } from "../../../queryClient";
import { useVideoJobActions, useVideoJobsQuery, useVideoProjectQuery, useVideoScenesQuery } from "../../../hooks/useVideoQueries";
import styles from "../styles/AiVideoRoute.module.css";

/** Enum-like backend statuses mapped to copy keys; unknown values render raw. */
type VideoStatus = "draft" | "queued" | "preparing" | "scripting" | "generating_audio" | "generating_visuals" | "rendering" | "completed" | "failed" | "canceled" | "cancelled";

const videoStatusKeys: Record<VideoStatus, TranslationKey> = {
  draft: "aiVideo.status.draft",
  queued: "aiVideo.status.queued",
  preparing: "aiVideo.status.preparing",
  scripting: "aiVideo.status.scripting",
  generating_audio: "aiVideo.status.generatingAudio",
  generating_visuals: "aiVideo.status.generatingVisuals",
  rendering: "aiVideo.status.rendering",
  completed: "aiVideo.status.completed",
  failed: "aiVideo.status.failed",
  canceled: "aiVideo.status.canceled",
  cancelled: "aiVideo.status.cancelled",
};

/** Translate one backend status token, falling back to the raw value. */
function videoStatusLabel(status: string, t: Translator): string {
  const key = (videoStatusKeys as Record<string, TranslationKey | undefined>)[status];
  return key ? t(key) : status;
}

/**
 * Video project workspace: job progress, scenes and SSE updates.
 */
export default function AiVideoProjectRoute() {
  const { projectId = "" } = useParams();
  const nav = useNavigate();
  const client = useQueryClient();
  const { t } = useI18n();
  const projectQuery = useVideoProjectQuery(projectId);
  const scenesQuery = useVideoScenesQuery(projectId);
  const jobsQuery = useVideoJobsQuery(projectId);
  const [busy, setBusy] = React.useState(false);
  const project = projectQuery.data;
  const scenes = scenesQuery.data ?? [];
  const job = jobsQuery.data?.[0] ?? null;
  const jobActions = useVideoJobActions(projectId, job);
  const controller = React.useRef<AbortController | null>(null);

  React.useEffect(() => {
    if (!projectId) return;
    controller.current?.abort();
    const controllerForRun = new AbortController();
    controller.current = controllerForRun;
    void teacherVideoApi.streamEvents(projectId, (event) => {
      if (event.type !== "status") return;
      client.setQueryData(queryKeys.videoJobs(projectId), (jobs: typeof jobsQuery.data) => {
        if (!jobs?.length) return jobs;
        return [{ ...jobs[0], status: event.status || jobs[0].status, stage: event.stage || jobs[0].stage, progress: event.progress ?? jobs[0].progress }, ...jobs.slice(1)];
      });
    }, controllerForRun.signal).catch(() => undefined);
    return () => controllerForRun.abort();
  }, [client, projectId]);

  const generate = async () => {
    if (!projectId || busy) return;
    setBusy(true);
    try {
      const response = await teacherVideoApi.generate(projectId, crypto.randomUUID());
      client.setQueryData(queryKeys.videoJobs(projectId), (jobs: typeof jobsQuery.data) => [response.data, ...(jobs ?? [])]);
    } finally {
      setBusy(false);
    }
  };

  const patchScene = useMutation({
    mutationFn: ({ sceneId, payload }: { sceneId: string; payload: Record<string, string> }) => teacherVideoApi.patchScene(projectId, sceneId, payload),
    onSuccess: ({ data }) => client.setQueryData([...queryKeys.videoProject(projectId), "scenes"], (items: typeof scenes) => items.map((item) => item.id === data.id ? data : item)),
  });

  if (!project) return <main className={styles.page}>{projectQuery.isError ? getApiErrorMessage(projectQuery.error, t("aiVideo.project.loadFailed")) : t("aiVideo.project.loading")}</main>;
  return <main className={styles.page}><button className={styles.back} onClick={() => nav("/teacher/ai-video")}>← {t("aiVideo.project.backToList")}</button><header className={styles.heading}><div><span>{project.provider.toUpperCase()} PROVIDER</span><h1>{project.title}</h1><p>{project.input_text || t("aiVideo.project.emptyScriptHint")}</p></div><button onClick={() => void generate()} disabled={busy}>{busy ? t("aiVideo.project.queueing") : t("aiVideo.project.generate")}</button></header>{job && <section className={styles.progress}><strong>{videoStatusLabel(job.status, t)}</strong><span>{job.stage}</span><div><i style={{ width: `${job.progress}%` }} /></div><small>{job.progress}% · job {job.id}</small>{job.error_message && <p className={styles.error}>{job.error_message}<button onClick={() => jobActions.retry.mutate()} disabled={jobActions.retry.isPending}>{t("aiVideo.project.retry")}</button><button onClick={() => jobActions.cancel.mutate()} disabled={jobActions.cancel.isPending}>{t("aiVideo.project.cancel")}</button></p>}</section>}<section className={styles.workspace}><aside><h2>{t("aiVideo.project.scenesTitle")}</h2>{scenes.map((scene) => <button className={styles.scene} key={scene.id}><b>{scene.order_index}</b><span>{scene.title}</span><small>{scene.duration_seconds}s</small></button>)}{!scenes.length && <p className={styles.empty}>{t("aiVideo.project.scenesEmpty")}</p>}</aside><article><h2>{t("aiVideo.project.scriptTitle")}</h2>{scenes.map((scene) => <div className={styles.sceneEditor} key={scene.id}><input defaultValue={scene.title} onBlur={(e) => patchScene.mutate({ sceneId: scene.id, payload: { title: e.target.value } })} /><textarea defaultValue={scene.narration} onBlur={(e) => patchScene.mutate({ sceneId: scene.id, payload: { narration: e.target.value } })} /><small>{scene.onscreen_text}</small></div>)}</article></section></main>;
}
