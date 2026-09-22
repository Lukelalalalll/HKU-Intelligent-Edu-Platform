import React from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { getApiErrorMessage, teacherVideoApi } from "../../../api";
import { queryKeys } from "../../../queryClient";
import { useVideoJobActions, useVideoJobsQuery, useVideoProjectQuery, useVideoScenesQuery } from "../../../hooks/useVideoQueries";
import styles from "../styles/AiVideoRoute.module.css";

export default function AiVideoProjectRoute() {
  const { projectId = "" } = useParams();
  const nav = useNavigate();
  const client = useQueryClient();
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

  if (!project) return <main className={styles.page}>{projectQuery.isError ? getApiErrorMessage(projectQuery.error, "项目加载失败，请返回重试。") : "正在加载…"}</main>;
  return <main className={styles.page}><button className={styles.back} onClick={() => nav("/teacher/ai-video")}>← 返回项目列表</button><header className={styles.heading}><div><span>{project.provider.toUpperCase()} PROVIDER</span><h1>{project.title}</h1><p>{project.input_text || "请在项目设置中补充讲稿或课程资料。"}</p></div><button onClick={() => void generate()} disabled={busy}>{busy ? "排队中…" : "生成视频"}</button></header>{job && <section className={styles.progress}><strong>{job.status}</strong><span>{job.stage}</span><div><i style={{ width: `${job.progress}%` }} /></div><small>{job.progress}% · job {job.id}</small>{job.error_message && <p className={styles.error}>{job.error_message}<button onClick={() => jobActions.retry.mutate()} disabled={jobActions.retry.isPending}>重试</button><button onClick={() => jobActions.cancel.mutate()} disabled={jobActions.cancel.isPending}>取消</button></p>}</section>}<section className={styles.workspace}><aside><h2>分镜</h2>{scenes.map((scene) => <button className={styles.scene} key={scene.id}><b>{scene.order_index}</b><span>{scene.title}</span><small>{scene.duration_seconds}s</small></button>)}{!scenes.length && <p className={styles.empty}>生成后会显示场景。</p>}</aside><article><h2>脚本与场景</h2>{scenes.map((scene) => <div className={styles.sceneEditor} key={scene.id}><input defaultValue={scene.title} onBlur={(e) => patchScene.mutate({ sceneId: scene.id, payload: { title: e.target.value } })} /><textarea defaultValue={scene.narration} onBlur={(e) => patchScene.mutate({ sceneId: scene.id, payload: { narration: e.target.value } })} /><small>{scene.onscreen_text}</small></div>)}</article></section></main>;
}
