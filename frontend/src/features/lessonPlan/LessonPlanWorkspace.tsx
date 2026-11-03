/**
 * Lesson plan workspace: outline, streaming conversation, A4 preview and
 * export controls for one project.
 *
 * The component owns every request. Presentational panels under the same
 * feature folder receive plain props so they stay easy to test.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";
import { getApiErrorMessage, isApiError, lessonPlanApi, type LessonPlanAsset, type LessonPlanPage, type LessonPlanState } from "../../api";
import { useI18n, type TranslationKey } from "../../i18n";
import { HKUConfirmDialog } from "../../shared/components/HKUDialog";
import LessonPlanChat from "./LessonPlanChat";
import LessonPlanEditor from "./LessonPlanEditor";
import LessonPlanPreview from "./LessonPlanPreview";
import LessonPlanSidebar from "./LessonPlanSidebar";
import { answerNumber, downloadBlob, downloadFilename, materialFileIssue, stageKey } from "./lessonPlanFormat";

const PAGE_STATUS_KEYS: Record<string, TranslationKey> = {
  ready: "lessonPlan.outline.status.ready",
  draft: "lessonPlan.outline.status.draft",
  edited: "lessonPlan.outline.status.edited",
  empty: "lessonPlan.outline.status.draft",
};

export type LessonPlanWorkspaceProps = {
  projectId: string;
};

/** Full-screen workspace for one lesson plan project. */
export default function LessonPlanWorkspace({ projectId }: LessonPlanWorkspaceProps) {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [data, setData] = useState<LessonPlanState | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [tab, setTab] = useState<"chat" | "preview">("chat");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [statusText, setStatusText] = useState("");
  const [chatError, setChatError] = useState<string | null>(null);
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [rewritingId, setRewritingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [editingPage, setEditingPage] = useState<LessonPlanPage | null>(null);
  const [confirmGenerateOpen, setConfirmGenerateOpen] = useState(false);
  const [format, setFormat] = useState<"pdf" | "markdown">("pdf");
  const [includeAnswers, setIncludeAnswers] = useState(true);
  const [blackWhite, setBlackWhite] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bootstrapped = useRef(false);
  const optionsInitialized = useRef(false);
  const pendingRetry = useRef<{ content: string; optionLabel?: string; bootstrap?: boolean } | null>(null);

  const applyState = useCallback((next: LessonPlanState) => {
    setData(next);
    setSelectedId((current) => (next.pages.some((page) => page.id === current) ? current : next.pages[0]?.id ?? null));
    if (!optionsInitialized.current) {
      optionsInitialized.current = true;
      setIncludeAnswers(next.answers.include_answers !== false);
    }
  }, []);

  const load = useCallback(async () => {
    const { data: next } = await lessonPlanApi.state(projectId);
    applyState(next);
    return next;
  }, [applyState, projectId]);

  const goHome = useCallback(() => {
    abortRef.current?.abort();
    navigate("/teacher/lesson-plan-agent");
  }, [navigate]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(false);
    bootstrapped.current = false;
    optionsInitialized.current = false;
    setData(null);
    lessonPlanApi
      .state(projectId)
      .then((response) => {
        if (cancelled) return;
        applyState(response.data);
        setLoading(false);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (isApiError(error) && error.status === 404) {
          toast.error(t("lessonPlan.toast.projectMissing"));
          goHome();
          return;
        }
        setLoadError(true);
        setLoading(false);
      });
    return () => {
      cancelled = true;
      abortRef.current?.abort();
    };
  }, [applyState, goHome, projectId, t]);

  const sendChat = useCallback(
    async (content: string, optionLabel?: string, bootstrap = false) => {
      if (busy) return;
      setBusy(true);
      setChatError(null);
      setStreamText("");
      setStatusText(t("lessonPlan.chat.thinking"));
      setPendingText(bootstrap ? null : content || optionLabel || null);
      pendingRetry.current = { content, optionLabel, bootstrap };
      const controller = new AbortController();
      abortRef.current = controller;
      const hadPages = Boolean(data?.pages.length);
      try {
        const complete = await lessonPlanApi.streamChat(
          projectId,
          { content, option_label: optionLabel, bootstrap },
          {
            onEvent: (event) => {
              if (event.type === "chunk" && event.chunk) setStreamText((current) => current + event.chunk);
            },
          },
          controller.signal,
        );
        if (complete) {
          const refreshed = await load();
          if (complete.mode === "refine" && complete.page_updates?.length) {
            const updated = complete.page_updates.length;
            toast.success(t(updated === 1 ? "lessonPlan.toast.pagesUpdated.one" : "lessonPlan.toast.pagesUpdated.other", { count: updated }));
          }
          if (!hadPages && refreshed.pages.length) setTab("preview");
        }
        setPendingText(null);
      } catch (error: unknown) {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setChatError(getApiErrorMessage(error, t("lessonPlan.toast.sendFailed")));
        }
      } finally {
        abortRef.current = null;
        setBusy(false);
        setStreamText("");
        setStatusText("");
      }
    },
    [busy, data?.pages.length, load, projectId, t],
  );

  useEffect(() => {
    if (loading || !data || bootstrapped.current) return;
    if (data.messages.length === 0) {
      bootstrapped.current = true;
      void sendChat("", undefined, true);
    }
  }, [data, loading, sendChat]);

  const runGenerate = useCallback(async () => {
    setConfirmGenerateOpen(false);
    setGenerating(true);
    try {
      const response = await lessonPlanApi.generate(projectId, {
        page_count: answerNumber(data?.answers.page_count) ?? undefined,
        include_answers: includeAnswers,
      });
      await load();
      setTab("preview");
      if (response.data.degraded) toast(t("lessonPlan.toast.degradedGenerated"));
      else toast.success(t("lessonPlan.toast.generated"));
    } catch (error: unknown) {
      toast.error(getApiErrorMessage(error, t("lessonPlan.toast.generateFailed")));
    } finally {
      setGenerating(false);
    }
  }, [data?.answers.page_count, includeAnswers, load, projectId, t]);

  const requestGenerate = useCallback(() => {
    if (data?.pages.length) setConfirmGenerateOpen(true);
    else void runGenerate();
  }, [data?.pages.length, runGenerate]);

  const rewritePage = useCallback(
    async (page: LessonPlanPage) => {
      setRewritingId(page.id);
      try {
        const response = await lessonPlanApi.regeneratePage(projectId, page.id);
        await load();
        if (response.data.degraded) toast(t("lessonPlan.toast.rewriteDegraded"));
        else toast.success(t("lessonPlan.toast.rewritten"));
      } catch (error: unknown) {
        toast.error(getApiErrorMessage(error, t("lessonPlan.toast.rewriteFailed")));
      } finally {
        setRewritingId(null);
      }
    },
    [load, projectId, t],
  );

  const savePage = useCallback(
    async (markdown: string) => {
      if (!editingPage) return;
      setSaving(true);
      try {
        await lessonPlanApi.savePage(projectId, editingPage.id, { document: { version: 2, markdown }, revision: editingPage.revision });
        await load();
        setEditingPage(null);
        toast.success(t("lessonPlan.toast.saved"));
      } catch (error: unknown) {
        if (isApiError(error) && error.status === 409) {
          toast.error(t("lessonPlan.toast.saveConflict"));
          await load();
          setEditingPage(null);
        } else {
          toast.error(getApiErrorMessage(error, t("lessonPlan.toast.saveFailed")));
        }
      } finally {
        setSaving(false);
      }
    },
    [editingPage, load, projectId, t],
  );

  const uploadFiles = useCallback(
    async (files: FileList | File[]) => {
      if (uploading || !files.length) return;
      setUploading(true);
      let uploaded = 0;
      for (const file of Array.from(files)) {
        const issue = materialFileIssue(file);
        if (issue === "type") { toast.error(t("lessonPlan.toast.unsupportedFile", { name: file.name })); continue; }
        if (issue === "size") { toast.error(t("lessonPlan.toast.fileTooLarge", { name: file.name })); continue; }
        try {
          await lessonPlanApi.upload(projectId, file);
          uploaded += 1;
        } catch (error: unknown) {
          toast.error(getApiErrorMessage(error, t("lessonPlan.toast.uploadFailed", { name: file.name })));
        }
      }
      if (uploaded) {
        await load();
        toast.success(t(uploaded === 1 ? "lessonPlan.toast.uploadSuccess.one" : "lessonPlan.toast.uploadSuccess.other", { count: uploaded }));
      }
      setUploading(false);
    },
    [load, projectId, t, uploading],
  );

  const deleteFile = useCallback(
    async (asset: LessonPlanAsset) => {
      try {
        await lessonPlanApi.deleteFile(projectId, asset.id);
        await load();
        toast.success(t("lessonPlan.toast.materialRemoved"));
      } catch (error: unknown) {
        toast.error(getApiErrorMessage(error, t("lessonPlan.toast.removeFailed")));
      }
    },
    [load, projectId, t],
  );

  const runExport = useCallback(async () => {
    if (!data?.pages.length || exporting) return;
    setExporting(true);
    try {
      if (format === "markdown") {
        const response = await lessonPlanApi.downloadMarkdown(projectId, includeAnswers);
        downloadBlob(response.data, downloadFilename(data.project.title, "md"));
      } else {
        const response = await lessonPlanApi.exportPdf(projectId, { include_answers: includeAnswers, black_white: blackWhite });
        if (response.data.status !== "completed") {
          toast.error(response.data.error || t("lessonPlan.toast.exportFailed"));
          return;
        }
        const file = await lessonPlanApi.downloadPdf(projectId, response.data.id);
        downloadBlob(file.data, downloadFilename(data.project.title, "pdf"));
      }
      toast.success(t("lessonPlan.toast.exportSuccess"));
      await load();
    } catch (error: unknown) {
      toast.error(getApiErrorMessage(error, t("lessonPlan.toast.exportFailed")));
    } finally {
      setExporting(false);
    }
  }, [blackWhite, data?.pages.length, data?.project.title, exporting, format, includeAnswers, load, projectId, t]);

  const retryChat = useCallback(() => {
    const pending = pendingRetry.current;
    if (!pending) return;
    void sendChat(pending.content, pending.optionLabel, pending.bootstrap);
  }, [sendChat]);

  const pages = data?.pages ?? [];
  const lastMessage = data?.messages[data.messages.length - 1];
  const question = lastMessage?.role === "assistant" ? lastMessage.payload.question ?? null : null;
  const answers = data?.answers ?? {};
  const subject = typeof answers.subject === "string" ? answers.subject : "";
  const grade = typeof answers.grade === "string" ? answers.grade : "";
  const duration = answerNumber(answers.duration_minutes);
  const activePage = pages.find((page) => page.id === selectedId) ?? pages[0] ?? null;
  const degraded = Boolean(data?.degraded);

  if (loading) {
    return (
      <div className="lesson-workspace lesson-workspace-loading">
        <span className="lesson-spinner" aria-hidden="true" />
        <p>{t("lessonPlan.workspace.loading")}</p>
      </div>
    );
  }

  if (loadError || !data) {
    return (
      <div className="lesson-workspace lesson-workspace-loading">
        <p>{t("lessonPlan.workspace.loadFailed")}</p>
        <div className="lesson-load-actions">
          <button type="button" className="lesson-button secondary" onClick={goHome}>{t("lessonPlan.workspace.backHome")}</button>
          <button type="button" className="lesson-button primary" onClick={() => void load().catch(() => setLoadError(true))}>{t("lessonPlan.workspace.retryLoad")}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="lesson-workspace">
      <header className="lesson-workspace-head">
        <button type="button" className="lesson-back" onClick={goHome} aria-label={t("lessonPlan.workspace.back")}>←</button>
        <div className="lesson-workspace-title">
          <span className="lesson-eyebrow">LESSON PLAN AGENT</span>
          <h1>{data.project.title}</h1>
        </div>
        <span className={`lesson-stage-pill stage-${data.project.current_stage}`}>{t(stageKey(data.project.current_stage))}</span>
        <div className="lesson-workspace-actions">
          <button type="button" className="lesson-button primary" onClick={requestGenerate} disabled={generating || busy}>
            {generating ? t("lessonPlan.workspace.generating") : pages.length ? t("lessonPlan.workspace.regenerate") : t("lessonPlan.workspace.generate")}
          </button>
        </div>
      </header>

      {degraded ? (
        <div className="lesson-degraded" role="status" title={data.degraded_reason}>
          <strong>{t("lessonPlan.workspace.degradedTitle")}</strong>
          <span>{t("lessonPlan.workspace.degradedBody")}</span>
        </div>
      ) : null}

      {generating ? (
        <div className="lesson-progress-strip" role="status">
          <i aria-hidden="true" />
          <span>{t("lessonPlan.workspace.generatingHint")}</span>
        </div>
      ) : null}

      <div className="lesson-workspace-grid">
        <aside className="lesson-outline">
          <div className="lesson-panel-head">
            <div>
              <span className="lesson-eyebrow">OUTLINE</span>
              <h2>{t("lessonPlan.outline.title")}</h2>
            </div>
            <strong>{pages.length}</strong>
          </div>
          {pages.length ? (
            pages.map((page, index) => (
              <button
                type="button"
                key={page.id}
                className={`lesson-outline-item ${page.id === activePage?.id ? "is-active" : ""}`}
                onClick={() => { setSelectedId(page.id); setTab("preview"); }}
              >
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <b>{page.title || t("lessonPlan.outline.untitled")}</b>
                  <small>{t(PAGE_STATUS_KEYS[page.status] ?? "lessonPlan.outline.status.draft")}</small>
                </div>
              </button>
            ))
          ) : (
            <p className="lesson-outline-empty">{t("lessonPlan.outline.empty")}</p>
          )}
        </aside>

        <main className="lesson-workspace-main">
          <div className="lesson-tabs" role="tablist" aria-label={t("lessonPlan.workspace.viewLabel")}>
            <button type="button" role="tab" aria-selected={tab === "chat"} className={tab === "chat" ? "is-active" : ""} onClick={() => setTab("chat")}>
              {t("lessonPlan.workspace.chatTab")}
            </button>
            <button type="button" role="tab" aria-selected={tab === "preview"} className={tab === "preview" ? "is-active" : ""} onClick={() => setTab("preview")} disabled={!pages.length}>
              {t("lessonPlan.workspace.previewTab")}
            </button>
          </div>

          {tab === "chat" ? (
            <LessonPlanChat
              messages={data.messages}
              question={question}
              busy={busy}
              streamText={streamText}
              statusText={statusText}
              error={chatError}
              pendingText={pendingText}
              hasPages={pages.length > 0}
              onSend={sendChat}
              onRetry={retryChat}
              onUpload={(files) => void uploadFiles(files)}
            />
          ) : (
            <LessonPlanPreview
              projectTitle={data.project.title}
              subject={subject}
              grade={grade}
              duration={duration}
              pages={pages}
              selectedId={activePage?.id ?? null}
              hideAnswers={!includeAnswers}
              rewriting={Boolean(rewritingId)}
              generating={generating}
              onSelect={(pageId) => setSelectedId(pageId)}
              onEdit={(page) => setEditingPage(page)}
              onRewrite={(page) => void rewritePage(page)}
              onGenerate={requestGenerate}
            />
          )}
        </main>

        <LessonPlanSidebar
          answers={answers}
          briefSummary={data.brief_summary}
          ready={data.ready_to_generate}
          assets={data.assets}
          hasPages={pages.length > 0}
          generating={generating}
          generateDisabled={busy}
          uploading={uploading}
          exporting={exporting}
          format={format}
          includeAnswers={includeAnswers}
          blackWhite={blackWhite}
          degraded={degraded}
          onGenerate={requestGenerate}
          onUpload={(files) => void uploadFiles(files)}
          onDeleteFile={(asset) => void deleteFile(asset)}
          onFormatChange={setFormat}
          onIncludeAnswersChange={setIncludeAnswers}
          onBlackWhiteChange={setBlackWhite}
          onExport={() => void runExport()}
        />
      </div>

      <LessonPlanEditor page={editingPage} saving={saving} onSave={(markdown) => void savePage(markdown)} onClose={() => setEditingPage(null)} />

      <HKUConfirmDialog
        open={confirmGenerateOpen}
        onClose={() => setConfirmGenerateOpen(false)}
        onConfirm={() => void runGenerate()}
        title={t("lessonPlan.dialog.regenerateTitle")}
        description={t("lessonPlan.dialog.regenerateBody")}
        confirmLabel={t("lessonPlan.dialog.regenerateConfirm")}
        loading={generating}
      />
    </div>
  );
}
