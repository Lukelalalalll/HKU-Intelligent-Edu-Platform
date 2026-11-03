/**
 * Course workspace modules shared by the course detail route.
 *
 * Each module owns its own loading, error and teacher-only actions.
 */
import React, { useState } from "react";
import toast from "react-hot-toast";
import { courseMaterialsApi, getApiErrorMessage, assignmentsApi, type Assignment, type CourseChapter, type CourseMaterial, type FileAsset, type MaterialKind, type Participant } from "../../../api";
import { useI18n } from "../../../i18n";
import FileUploadModal from "../../../shared/components/FileUploadModal";
import styles from "../styles/CoursesRoute.module.css";

/**
 * Participant roster; contact details are only rendered for teachers.
 */
export function ParticipantModule({ participants, loading, error, isTeacher, currentUserId }: { participants: Participant[]; loading: boolean; error: boolean; isTeacher: boolean; currentUserId?: string }) {
  const { t } = useI18n();
  const countLabel = t(participants.length === 1 ? "courses.participants.count.one" : "courses.participants.count.other", { count: participants.length });
  return <div className={styles.participantContent}>
    <header className={styles.participantHeading}><div><p className="eyebrow">COURSE PARTICIPANTS</p><h2>{t("courses.participants.title")}</h2><span>{countLabel}</span></div><i className="fas fa-user-group" /></header>
    {loading ? <div className={styles.participantState}><i className="fas fa-circle-notch fa-spin" /><strong>{t("courses.participants.loading")}</strong></div> : error ? <div className={styles.participantState}><i className="fas fa-circle-exclamation" /><strong>{t("courses.participants.loadError")}</strong><span>{t("courses.common.retryHint")}</span></div> : !participants.length ? <div className={styles.participantState}><i className="fas fa-users-slash" /><strong>{t("courses.participants.emptyTitle")}</strong><span>{t("courses.participants.emptyHint")}</span></div> : <div className={styles.participantGrid}>{participants.map((participant) => <ParticipantCard key={participant.id} participant={participant} detailed={isTeacher} current={participant.id === currentUserId} />)}</div>}
  </div>;
}

/**
 * Chapter list plus material upload, rename, reorder and delete.
 */
export function MaterialsModule({ courseId, kind, chapters, loading, error, selectedChapterId, onSelectChapter, onRefresh, isTeacher }: { courseId: string; kind: MaterialKind; chapters: CourseChapter[]; loading: boolean; error: boolean; selectedChapterId: string | null; onSelectChapter: (id: string) => void; onRefresh: () => Promise<void>; isTeacher: boolean }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const selectedChapter = chapters.find((chapter) => chapter.id === selectedChapterId) || null;
  const label = kind === "lecture" ? t("courses.materials.lectureFiles") : t("courses.materials.tutorialFiles");
  const totalMaterials = chapters.reduce((total, chapter) => total + chapter.material_count, 0);
  const chapterCountLabel = t(chapters.length === 1 ? "courses.materials.chapterCount.one" : "courses.materials.chapterCount.other", { count: chapters.length });
  const fileCountLabel = t(totalMaterials === 1 ? "courses.materials.fileCount.one" : "courses.materials.fileCount.other", { count: totalMaterials });

  const createChapter = async () => {
    const title = window.prompt(t("courses.materials.chapterPrompt"), t("courses.materials.chapterDefaultTitle", { number: chapters.length + 1 }))?.trim();
    if (!title) return;
    setBusy(true);
    try { await courseMaterialsApi.createChapter(courseId, { kind, title }); await onRefresh(); toast.success(t("courses.materials.chapterCreated")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.materials.chapterCreateFailed"))); }
    finally { setBusy(false); }
  };

  const renameChapter = async (chapter: CourseChapter) => {
    const title = window.prompt(t("courses.materials.chapterRenamePrompt"), chapter.title)?.trim();
    if (!title || title === chapter.title) return;
    setBusy(true);
    try { await courseMaterialsApi.updateChapter(courseId, chapter.id, { title }); await onRefresh(); toast.success(t("courses.materials.chapterUpdated")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.materials.chapterUpdateFailed"))); }
    finally { setBusy(false); }
  };

  const moveChapter = async (chapter: CourseChapter, offset: number) => {
    const index = chapters.findIndex((item) => item.id === chapter.id);
    const next = index + offset;
    if (next < 0 || next >= chapters.length) return;
    setBusy(true);
    try { await courseMaterialsApi.updateChapter(courseId, chapter.id, { sort_order: next }); await onRefresh(); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.materials.chapterReorderFailed"))); }
    finally { setBusy(false); }
  };

  const deleteChapter = async (chapter: CourseChapter) => {
    if (!window.confirm(t("courses.materials.chapterDeleteConfirm", { title: chapter.title }))) return;
    setBusy(true);
    try { await courseMaterialsApi.deleteChapter(courseId, chapter.id); await onRefresh(); toast.success(t("courses.materials.chapterDeleted")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.materials.chapterDeleteFailed"))); }
    finally { setBusy(false); }
  };

  const uploadFiles = async (files: FileList | null) => {
    if (!selectedChapter || !files?.length) return;
    setBusy(true);
    try { for (const file of Array.from(files)) await courseMaterialsApi.upload(courseId, selectedChapter.id, file); await onRefresh(); toast.success(t("courses.materials.uploadSuccess")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.materials.uploadFailed"))); }
    finally { setBusy(false); }
  };

  const attachAssets = async (assets: FileAsset[]) => {
    let chapterId = selectedChapter?.id;
    if (!chapterId) {
      const title = window.prompt(t("courses.materials.chapterPrompt"), t("courses.materials.chapterDefaultTitle", { number: chapters.length + 1 }))?.trim();
      if (!title) return;
      chapterId = (await courseMaterialsApi.createChapter(courseId, { kind, title })).data.id;
    }
    setBusy(true);
    try {
      for (const asset of assets) {
        await courseMaterialsApi.attach(courseId, { file_asset_id: asset.id, kind, chapter_id: chapterId });
      }
      await onRefresh();
      toast.success(t("courses.materials.uploadSuccess"));
    } catch (error: unknown) {
      toast.error(getApiErrorMessage(error, t("courses.materials.uploadFailed")));
    } finally {
      setBusy(false);
    }
  };

  const deleteMaterial = async (material: CourseMaterial) => {
    if (!window.confirm(t("courses.materials.materialDeleteConfirm", { title: material.title }))) return;
    setBusy(true);
    try { await courseMaterialsApi.delete(courseId, material.id); await onRefresh(); toast.success(t("courses.materials.materialDeleted")); }
    catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.materials.materialDeleteFailed"))); }
    finally { setBusy(false); }
  };

  return <div className={styles.materialsContent}>
    <header className={styles.materialsHeading}><div><p className="eyebrow">COURSE MATERIALS</p><h2>{label}</h2><span>{chapterCountLabel} · {fileCountLabel}</span></div><i className="fas fa-folder-open" /></header>
    {loading ? <div className={styles.materialsState}><i className="fas fa-circle-notch fa-spin" /><strong>{t("courses.materials.loading")}</strong></div> : error ? <div className={styles.materialsState}><i className="fas fa-circle-exclamation" /><strong>{t("courses.materials.loadError")}</strong><span>{t("courses.common.retryHint")}</span></div> : <div className={styles.materialsWorkspace}>
      <aside className={styles.chapterPanel}><div className={styles.chapterPanelHeader}><div><span>CHAPTERS</span><strong>{t("courses.materials.chapterList")}</strong></div>{isTeacher && <button type="button" className="primary-action" onClick={() => void createChapter()} disabled={busy}><i className="fas fa-plus" /> {t("courses.materials.newChapter")}</button>}</div>
        {!chapters.length ? <div className={styles.chapterEmpty}><i className="fas fa-list" /><span>{isTeacher ? t("courses.materials.createChapterFirst") : t("courses.materials.noChapters")}</span></div> : <div className={styles.chapterList}>{chapters.map((chapter, index) => <div key={chapter.id} className={`${styles.chapterItem} ${chapter.id === selectedChapterId ? styles.chapterItemActive : ""}`}><button type="button" onClick={() => onSelectChapter(chapter.id)}><span className={styles.chapterIndex}>{String(index + 1).padStart(2, "0")}</span><span><strong>{chapter.title}</strong><small>{t(chapter.material_count === 1 ? "courses.materials.fileCount.one" : "courses.materials.fileCount.other", { count: chapter.material_count })}</small></span></button>{isTeacher && <div className={styles.chapterActions}><button type="button" title={t("courses.materials.moveUp")} disabled={busy || index === 0} onClick={() => void moveChapter(chapter, -1)}><i className="fas fa-chevron-up" /></button><button type="button" title={t("courses.materials.moveDown")} disabled={busy || index === chapters.length - 1} onClick={() => void moveChapter(chapter, 1)}><i className="fas fa-chevron-down" /></button><button type="button" title={t("courses.materials.rename")} disabled={busy} onClick={() => void renameChapter(chapter)}><i className="fas fa-pen" /></button><button type="button" title={t("common.actions.delete")} disabled={busy} onClick={() => void deleteChapter(chapter)}><i className="fas fa-trash" /></button></div>}</div>)}</div>}
      </aside>
      <main className={styles.materialsMain}>{selectedChapter ? <><div className={styles.chapterTitleRow}><div><p className="eyebrow">CHAPTER {String(chapters.indexOf(selectedChapter) + 1).padStart(2, "0")}</p><h3>{selectedChapter.title}</h3><span>{t(selectedChapter.material_count === 1 ? "courses.materials.materialCount.one" : "courses.materials.materialCount.other", { count: selectedChapter.material_count })}</span></div>{isTeacher && <button type="button" className="primary-action" onClick={() => setModalOpen(true)} disabled={busy}><i className="fas fa-upload" /> {t("courses.materials.uploadMaterials")}</button>}</div>{selectedChapter.materials.length ? <div className={styles.materialGrid}>{selectedChapter.materials.map((material) => <MaterialCard key={material.id} courseId={courseId} material={material} isTeacher={isTeacher} busy={busy} onDelete={() => void deleteMaterial(material)} />)}</div> : <div className={styles.materialsState}><i className="fas fa-file-circle-plus" /><strong>{isTeacher ? t("courses.materials.noMaterialsTeacher") : t("courses.materials.noMaterialsStudent")}</strong><span>{isTeacher ? t("courses.materials.noMaterialsTeacherHint") : t("courses.materials.noMaterialsStudentHint")}</span>{isTeacher && <button type="button" className="secondary-action" onClick={() => setModalOpen(true)} disabled={busy}><i className="fas fa-upload" /> {t("courses.materials.uploadFirst")}</button>}</div>}</> : <div className={styles.materialsState}><i className="fas fa-folder-open" /><strong>{isTeacher ? t("courses.materials.startOrganizing") : t("courses.materials.noCourseMaterials")}</strong><span>{isTeacher ? t("courses.materials.startOrganizingHint") : t("courses.materials.noPublishedMaterials")}</span>{isTeacher && <button type="button" className="primary-action" onClick={() => void createChapter()} disabled={busy}><i className="fas fa-plus" /> {t("courses.materials.newChapterCta")}</button>}</div>}</main>
    </div>}
    <FileUploadModal open={modalOpen} onClose={() => setModalOpen(false)} onSubmit={attachAssets} title={kind === "lecture" ? t("courses.materials.uploadLectureTitle") : t("courses.materials.uploadTutorialTitle")} />
  </div>;
}

/**
 * Assignment composer and list for one course.
 */
export function AssignmentsModule({ courseId, assignments, loading, error, isTeacher, onRefresh, onGrade }: { courseId: string; assignments: Assignment[]; loading: boolean; error: boolean; isTeacher: boolean; onRefresh: () => Promise<void>; onGrade: (id: string) => void }) {
  const { t, formatDate } = useI18n();
  const [form, setForm] = useState({ title: "", description: "", due_at: "", max_score: "100" }); const [assets, setAssets] = useState<FileAsset[]>([]); const [modalOpen, setModalOpen] = useState(false); const [busy, setBusy] = useState(false);
  const countLabel = t(assignments.length === 1 ? "courses.assignments.count.one" : "courses.assignments.count.other", { count: assignments.length });
  const create = async () => { if (!form.title.trim()) return; setBusy(true); try { await assignmentsApi.create(courseId, { ...form, due_at: form.due_at || null, max_score: Number(form.max_score), file_asset_ids: assets.map((asset) => asset.id) }); setForm({ title: "", description: "", due_at: "", max_score: "100" }); setAssets([]); await onRefresh(); toast.success(t("courses.assignments.published")); } catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.assignments.publishFailed"))); } finally { setBusy(false); } };
  return <div className={styles.assignmentsContent}><header className={styles.materialsHeading}><div><p className="eyebrow">COURSEWORK</p><h2>{t("courses.assignments.title")}</h2><span>{countLabel}</span></div>{isTeacher && <i className="fas fa-file-pen" />}</header>{isTeacher && <section className={styles.assignmentComposer}><input placeholder={t("courses.assignments.titlePlaceholder")} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /><textarea placeholder={t("courses.assignments.descriptionPlaceholder")} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /><div className={styles.assignmentFormRow}><label>{t("courses.assignments.dueLabel")}<input type="datetime-local" value={form.due_at} onChange={(e) => setForm({ ...form, due_at: e.target.value })} /></label><label>{t("courses.assignments.maxScoreLabel")}<input type="number" min="1" value={form.max_score} onChange={(e) => setForm({ ...form, max_score: e.target.value })} /></label></div><div className={styles.assignmentComposerActions}><button type="button" className="secondary-action" onClick={() => setModalOpen(true)}>{t("courses.assignments.addAttachments", { count: assets.length })}</button><button type="button" className="primary-action" disabled={busy || !form.title.trim()} onClick={() => void create()}>{busy ? t("courses.assignments.publishing") : t("courses.assignments.publish")}</button></div></section>}{loading ? <div className={styles.materialsState}>{t("courses.assignments.loading")}</div> : error ? <div className={styles.materialsState}>{t("courses.assignments.loadError")}</div> : assignments.length ? <div className={styles.assignmentGrid}>{assignments.map((item) => <article className={styles.assignmentCard} key={item.id}><div><span className={styles.assignmentStatus}>{!item.status || item.status === "published" ? t("courses.assignments.publishedStatus") : item.status}</span><h3>{item.title}</h3><p>{item.description || t("courses.assignments.noDescription")}</p>{item.attachments?.length ? <div className={styles.assignmentAttachments}>{item.attachments.map((attachment) => <a key={attachment.id} href={attachment.download_url} target="_blank" rel="noreferrer"><i className="fas fa-paperclip" /> {attachment.file_name}</a>)}</div> : null}</div><footer><span><i className="fas fa-calendar" /> {item.due_at ? formatDate(item.due_at, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : t("courses.assignments.noDueDate")}</span><span><i className="fas fa-star" /> {t("courses.assignments.score", { count: item.max_score })}</span><span><i className="fas fa-paperclip" /> {t((item.attachments?.length || 0) === 1 ? "courses.assignments.attachmentCount.one" : "courses.assignments.attachmentCount.other", { count: item.attachments?.length || 0 })}</span>{isTeacher && <button type="button" className="secondary-action" onClick={() => onGrade(item.id)}>{t("courses.assignments.grade")}</button>}</footer></article>)}</div> : <div className={styles.materialsState}><i className="fas fa-file-circle-plus" /><strong>{t("courses.assignments.emptyTitle")}</strong><span>{isTeacher ? t("courses.assignments.emptyTeacherHint") : t("courses.assignments.emptyStudentHint")}</span></div>}<FileUploadModal open={modalOpen} onClose={() => setModalOpen(false)} onSubmit={async (items) => setAssets(items)} title={t("courses.assignments.addAttachmentsTitle")} /></div>;
}

function MaterialCard({ courseId, material, isTeacher, busy, onDelete }: { courseId: string; material: CourseMaterial; isTeacher: boolean; busy: boolean; onDelete: () => void }) {
  const { t, formatDate } = useI18n();
  const download = async () => {
    try {
      const response = await courseMaterialsApi.download(courseId, material.id);
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = material.file_name; anchor.click(); URL.revokeObjectURL(url);
    } catch (error: unknown) { toast.error(getApiErrorMessage(error, t("courses.materials.downloadFailed"))); }
  };
  const processing = material.processing_status && !["ready", "partial_ready"].includes(material.processing_status);
  return <article className={styles.materialCard}><div className={styles.materialIcon}><i className={`fas ${material.mime_type.includes("pdf") ? "fa-file-pdf" : material.mime_type.startsWith("image/") ? "fa-file-image" : "fa-file-lines"}`} /></div><div className={styles.materialInfo}><strong title={material.title}>{material.title}</strong><span>{material.file_name}</span><small>{formatBytes(material.size_bytes)} · {formatDate(material.uploaded_at)}</small>{processing ? <small>{t("courses.materials.processing", { status: material.processing_status ?? "" })}</small> : material.processing_status === "partial_ready" ? <small>{t("courses.materials.partialReady")}</small> : material.processing_status === "ready" ? <small>{t("courses.materials.ready")}</small> : null}</div><div className={styles.materialActions}><button type="button" className="secondary-action" onClick={() => void download()}><i className="fas fa-download" /> {t("courses.materials.download")}</button>{isTeacher && <button type="button" className={styles.iconAction} title={t("common.actions.delete")} disabled={busy} onClick={onDelete}><i className="fas fa-trash" /></button>}</div></article>;
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function ParticipantCard({ participant, detailed, current }: { participant: Participant; detailed: boolean; current: boolean }) {
  const { t, formatDate } = useI18n();
  const initials = (participant.name || participant.username || participant.email).slice(0, 1).toUpperCase();
  return <article className={`${styles.participantCard} ${current ? styles.participantCardCurrent : ""}`}>
    <div className={styles.participantIdentity}>{detailed && (participant.avatar_url ? <img className={styles.participantAvatar} src={participant.avatar_url} alt="" /> : <span className={styles.participantAvatar}>{initials}</span>)}<div><strong>{participant.name || participant.email}</strong>{current && <small className={styles.participantCurrentLabel}>{t("courses.participants.you")}</small>}</div></div>
    <div className={styles.participantDetails}><span><i className="fas fa-envelope" />{participant.email}</span>{detailed && <><span><i className="fas fa-at" />{participant.username}</span>{participant.enrolled_at && <span><i className="fas fa-calendar-plus" />{t("courses.participants.joinedAt", { date: formatDate(participant.enrolled_at) })}</span>}</>}</div>
  </article>;
}
