import React from "react";
import { useNavigate } from "react-router-dom";
import { api, fileApi, teacherVideoApi, type Course, type VideoProject } from "../../../api";
import { useI18n, type TranslationKey, type Translator } from "../../../i18n";
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
 * Video project list and creation form.
 */
export default function AiVideoRoute() {
  const [projects, setProjects] = React.useState<VideoProject[]>([]); const [courses, setCourses] = React.useState<Course[]>([]); const [title, setTitle] = React.useState(""); const [text, setText] = React.useState(""); const [courseId, setCourseId] = React.useState(""); const [objectives, setObjectives] = React.useState(""); const [audience, setAudience] = React.useState(""); const [duration, setDuration] = React.useState(120); const [language, setLanguage] = React.useState("zh-HK"); const [style, setStyle] = React.useState("lecture"); const [provider, setProvider] = React.useState<"coze" | "local">("local"); const [voice, setVoice] = React.useState(true); const [captions, setCaptions] = React.useState(true); const [avatar, setAvatar] = React.useState(false); const [file, setFile] = React.useState<File | null>(null); const [busy, setBusy] = React.useState(false); const nav = useNavigate(); const { t, formatDate } = useI18n();
  const load = React.useCallback(() => Promise.all([teacherVideoApi.listProjects(), api.get<Course[]>("/courses")]).then(([p, c]) => { setProjects(p.data); setCourses(c.data); }).catch(() => undefined), []); React.useEffect(() => { void load(); }, [load]);
  const create = async (event: React.FormEvent) => { event.preventDefault(); if (!title.trim()) return; setBusy(true); try { const p = (await teacherVideoApi.createProject({ title, course_id: courseId || undefined, input_text: text, provider, learning_objectives: objectives.split("\n").map((x) => x.trim()).filter(Boolean), audience, duration_seconds: duration, language, style, voice_enabled: voice, captions_enabled: captions, avatar_enabled: avatar })).data; if (file) { const uploaded = await fileApi.upload(file); await teacherVideoApi.addSource(p.id, { file_asset_id: uploaded.data.id, source_type: "upload", title: file.name }); } nav(`/teacher/ai-video/${p.id}`); } finally { setBusy(false); } };
  return <main className={styles.page}><header className={styles.heading}><div><span>AI TEACHING VIDEO</span><h1>{t("aiVideo.list.title")}</h1><p>{t("aiVideo.list.subtitle")}</p></div><form className={styles.create} onSubmit={create}><input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("aiVideo.form.titlePlaceholder")} /><select value={courseId} onChange={(e) => setCourseId(e.target.value)}><option value="">{t("aiVideo.form.coursePlaceholder")}</option>{courses.map((course) => <option value={course.id} key={course.id}>{course.code} · {course.name}</option>)}</select><textarea value={text} onChange={(e) => setText(e.target.value)} placeholder={t("aiVideo.form.scriptPlaceholder")} rows={3} /><textarea value={objectives} onChange={(e) => setObjectives(e.target.value)} placeholder={t("aiVideo.form.objectivesPlaceholder")} rows={2} /><input value={audience} onChange={(e) => setAudience(e.target.value)} placeholder={t("aiVideo.form.audiencePlaceholder")} /><div className={styles.row}><label>{t("aiVideo.form.durationLabel")} <input type="number" min={15} max={900} value={duration} onChange={(e) => setDuration(Number(e.target.value))} /></label><label>{t("aiVideo.form.languageLabel")} <select value={language} onChange={(e) => setLanguage(e.target.value)}><option value="zh-HK">{t("aiVideo.form.languageTraditionalChinese")}</option><option value="zh-CN">{t("aiVideo.form.languageSimplifiedChinese")}</option><option value="en">{t("aiVideo.form.languageEnglish")}</option></select></label></div><div className={styles.row}><label>{t("aiVideo.form.styleLabel")} <select value={style} onChange={(e) => setStyle(e.target.value)}><option value="lecture">{t("aiVideo.form.styleLecture")}</option><option value="storytelling">{t("aiVideo.form.styleStorytelling")}</option><option value="summary">{t("aiVideo.form.styleSummary")}</option></select></label><label>{t("aiVideo.form.materialLabel")} <input type="file" accept=".pdf,.ppt,.pptx,.doc,.docx,.png,.jpg,.jpeg" onChange={(e) => setFile(e.target.files?.[0] || null)} /></label></div><select value={provider} onChange={(e) => setProvider(e.target.value as "coze" | "local")}><option value="local">{t("aiVideo.provider.local")}</option><option value="coze">{t("aiVideo.provider.coze")}</option></select><div className={styles.checks}><label><input type="checkbox" checked={voice} onChange={(e) => setVoice(e.target.checked)} />{t("aiVideo.form.voice")}</label><label><input type="checkbox" checked={captions} onChange={(e) => setCaptions(e.target.checked)} />{t("aiVideo.form.captions")}</label><label><input type="checkbox" checked={avatar} onChange={(e) => setAvatar(e.target.checked)} />{t("aiVideo.form.avatar")}</label></div><button disabled={busy || !title.trim()}>{busy ? t("aiVideo.form.submitting") : t("aiVideo.form.submit")}</button></form></header><section className={styles.list}><h2>{t("aiVideo.list.myProjects")}</h2>{projects.length ? projects.map((p) => <button className={styles.card} key={p.id} onClick={() => nav(`/teacher/ai-video/${p.id}`)}><strong>{p.title}</strong><span>{p.provider} · {videoStatusLabel(p.status, t)} · {t("aiVideo.list.durationSeconds", { count: p.duration_seconds })}</span><small>{formatDate(p.updated_at, { dateStyle: "medium", timeStyle: "short" })}</small></button>) : <div className={styles.empty}>{t("aiVideo.list.empty")}</div>}</section></main>;
}
