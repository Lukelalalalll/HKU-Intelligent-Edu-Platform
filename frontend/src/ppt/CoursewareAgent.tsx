/**
 * PPT studio workspace: requirement chat, outline, visual research, theme,
 * layout generation, preview editing and presentation.
 *
 * The component owns every request; the surfaces under ``./studio`` stay
 * presentational and receive a single typed model.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";
import type { PptMessage, PptPage, PptPagePatch, PptProject, PptRequirement, PptSource, PptTheme, RequirementChatResponse } from "../api";
import { pptApi } from "../api";
import { HKUConfirmDialog } from "../shared/components/HKUDialog";
import { getApiErrorMessage } from "../lib/apiClient";
import { usePptAutosave } from "../hooks/usePptAutosave";
import { usePptGeneration } from "../hooks/usePptGeneration";
import { useI18n } from "../i18n";
import StudioHome from "./studio/StudioHome";
import StudioWorkspace from "./studio/StudioWorkspace";
import { StudioIcon } from "./studio/icons";
import { defaultSurface } from "./studio/stages";
import type { ExportState, StudioActions, StudioModel, StudioSurface } from "./studio/types";
import "./studio/studio.css";
import "./studio/studio-globals.css";

const TERMINAL = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);
const EMPTY_REQUIREMENT = (projectId: string): PptRequirement => ({
  project_id: projectId,
  status: "pending",
  page_count_target: null,
  answers: {},
  questions: [],
  page_count_options: [],
  ready_to_outline: false,
  suggested_additions: [],
  brief_summary: "",
});

/**
 * Drive one PPT project through the studio surfaces.
 */
export default function CoursewareAgent() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const { projectId } = useParams<{ projectId?: string }>();
  const [projects, setProjects] = useState<PptProject[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [projectsError, setProjectsError] = useState<string | null>(null);
  const [active, setActive] = useState<PptProject | null>(null);
  const [pages, setPages] = useState<PptPage[]>([]);
  const [messages, setMessages] = useState<PptMessage[]>([]);
  const [requirement, setRequirement] = useState<PptRequirement | null>(null);
  const [sources, setSources] = useState<PptSource[]>([]);
  const [themes, setThemes] = useState<PptTheme[]>([]);
  const [selected, setSelected] = useState(0);
  const [surface, setSurface] = useState<StudioSurface>("start");
  const [creating, setCreating] = useState(false);
  const [outlineGenerating, setOutlineGenerating] = useState(false);
  const [visualRunning, setVisualRunning] = useState(false);
  const [projectLoading, setProjectLoading] = useState(Boolean(projectId));
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<PptProject | null>(null);
  const [removingIds, setRemovingIds] = useState<Record<string, boolean>>({});
  const [exportState, setExportState] = useState<ExportState>("idle");
  const activeRef = useRef<PptProject | null>(null);
  const previousProjectId = useRef<string | undefined>(projectId);
  const visualTimerRef = useRef<number | null>(null);
  const exportPollRef = useRef<number | null>(null);
  const tRef = useRef(t);
  activeRef.current = active;
  tRef.current = t;

  const refresh = useCallback(async (project?: PptProject | null): Promise<PptPage[]> => {
    const target = project || activeRef.current;
    if (!target) return [];
    const [projectResponse, pagesResponse, messagesResponse, requirementResponse, sourcesResponse] = await Promise.all([
      pptApi.project(target.id),
      pptApi.pages(target.id),
      pptApi.messages(target.id),
      pptApi.requirements(target.id),
      pptApi.sources(target.id),
    ]);
    const items = [...pagesResponse.data.items].sort((a, b) => a.sort_order - b.sort_order);
    setActive(projectResponse.data);
    setPages(items);
    setMessages(messagesResponse.data.items);
    setRequirement(requirementResponse.data);
    setSources(sourcesResponse.data.items);
    return items;
  }, []);

  const refreshMessages = useCallback(async () => {
    const target = activeRef.current;
    if (!target) return;
    const { data } = await pptApi.messages(target.id);
    setMessages(data.items);
  }, []);

  const loadProjects = useCallback(async () => {
    setProjectsLoading(true);
    setProjectsError(null);
    try {
      const { data } = await pptApi.projects();
      setProjects([...data.items].sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at)));
    } catch (error) {
      setProjectsError(getApiErrorMessage(error, t("coursewareAgent.home.loadFailed")));
    } finally {
      setProjectsLoading(false);
    }
  }, [t]);

  useEffect(() => { void loadProjects(); }, [loadProjects]);
  useEffect(() => { pptApi.themes().then((response) => setThemes(response.data.items)).catch(() => undefined); }, []);
  useEffect(() => {
    const previous = previousProjectId.current;
    previousProjectId.current = projectId;
    if (!projectId && previous) void loadProjects();
  }, [projectId, loadProjects]);

  useEffect(() => {
    let cancelled = false;
    if (!projectId) {
      setProjectLoading(false);
      setActive(null); setPages([]); setMessages([]); setRequirement(null); setSources([]); setSelected(0); setSurface("start");
      return () => { cancelled = true; };
    }
    setProjectLoading(true);
    setActive(null);
    (async () => {
      try {
        const { data } = await pptApi.project(projectId);
        if (cancelled) return;
        const items = await refresh(data);
        if (cancelled) return;
        setSurface(defaultSurface(data, items));
        setSelected(0);
      } catch {
        if (!cancelled) {
          toast.error(tRef.current("coursewareAgent.project.notFound"));
          navigate("/teacher/courseware-agent", { replace: true });
        }
      } finally {
        if (!cancelled) setProjectLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [projectId, navigate, refresh]);

  useEffect(() => {
    setSelected((current) => Math.min(current, Math.max(0, pages.length - 1)));
  }, [pages.length]);

  useEffect(() => () => {
    if (visualTimerRef.current) window.clearInterval(visualTimerRef.current);
    if (exportPollRef.current) window.clearInterval(exportPollRef.current);
  }, []);

  const uploadFiles = useCallback(async (files: FileList | File[], project: PptProject | null = activeRef.current) => {
    if (!project) return;
    try {
      for (const file of Array.from(files)) await pptApi.upload(project.id, file);
      await refresh(project);
      toast.success(t("coursewareAgent.project.materialsAdded"));
    } catch (error) {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.project.materialsUploadFailed")));
    }
  }, [refresh, t]);

  const create = useCallback(async (text: string, files: File[] = []) => {
    if (!text.trim() || creating) return;
    setCreating(true);
    try {
      const { data } = await pptApi.createProject({ title: text.trim().slice(0, 32), request_text: text.trim() });
      setProjects((items) => [data, ...items]);
      if (files.length) await uploadFiles(files, data);
      navigate(`/teacher/courseware-agent/${data.id}`);
    } catch (error) {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.project.createFailed")));
    } finally {
      setCreating(false);
    }
  }, [creating, navigate, t, uploadFiles]);

  const confirmRemoveProject = async () => {
    const project = deleteCandidate;
    if (!project || deletingId) return;
    setDeletingId(project.id);
    try {
      await pptApi.deleteProject(project.id);
      setDeleteCandidate(null);
      setRemovingIds((items) => ({ ...items, [project.id]: true }));
      window.setTimeout(() => {
        setProjects((items) => items.filter((item) => item.id !== project.id));
        setRemovingIds((items) => { const next = { ...items }; delete next[project.id]; return next; });
      }, 420);
      toast.success(t("coursewareAgent.project.deleted"));
      if (projectId === project.id) navigate("/teacher/courseware-agent", { replace: true });
    } catch (error) {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.project.deleteFailed")));
    } finally {
      setDeletingId(null);
    }
  };

  const generateOutline = async () => {
    const project = activeRef.current;
    if (!project || !requirement?.ready_to_outline || outlineGenerating) return;
    setOutlineGenerating(true);
    setSurface("outline");
    try {
      await pptApi.generateOutline(project.id, { page_count_target: project.page_count_target || requirement.page_count_target || 10 });
      await refresh();
      toast.success(t("coursewareAgent.outline.generated"));
    } catch (error) {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.outline.generateFailed")));
      setSurface("start");
    } finally {
      setOutlineGenerating(false);
    }
  };

  const confirmOutline = async () => {
    const project = activeRef.current;
    if (!project) return;
    try {
      await pptApi.confirmCheckpoint(project.id, "outline_confirm");
      await refresh();
      setSurface("visual");
      toast.success(t("coursewareAgent.outline.confirmed"));
    } catch (error) {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.outline.confirmFirst")));
    }
  };

  const reorderPages = async (ids: string[]) => {
    const project = activeRef.current;
    if (!project) return;
    const selectedPageId = pages[selected]?.id;
    try {
      const { data } = await pptApi.patchStoryboard(project.id, ids);
      const nextPages = [...data.items].sort((a, b) => a.sort_order - b.sort_order);
      setPages(nextPages);
      const nextSelected = selectedPageId ? nextPages.findIndex((item) => item.id === selectedPageId) : 0;
      setSelected(nextSelected >= 0 ? nextSelected : 0);
    } catch (error) {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.editor.orderSaveFailed")));
    }
  };

  const patchPage = async (page: PptPage, payload: PptPagePatch) => {
    const project = activeRef.current;
    if (!project) throw new Error("missing project");
    const { data } = await pptApi.patchPage(project.id, page.id, payload);
    setPages((items) => items.map((item) => item.id === data.id ? data : item));
    return data;
  };

  const runVisualResearch = async () => {
    const project = activeRef.current;
    if (!project || visualRunning) return;
    setVisualRunning(true);
    try {
      const { data } = await pptApi.batch(project.id, "project_batch_visual");
      const job = (data as any)?.id ? data : (data as any)?.result;
      await refresh();
      toast.success(job?.id ? t("coursewareAgent.visual.backgroundStarted") : t("coursewareAgent.visual.submitted"));
      if (!job?.id) { setVisualRunning(false); return; }
      const timer = window.setInterval(async () => {
        try {
          const { data: state } = await pptApi.generationJob(project.id, job.id);
          await refresh();
          if (TERMINAL.has(state.status)) {
            window.clearInterval(timer);
            visualTimerRef.current = null;
            setVisualRunning(false);
            if (state.status === "completed") toast.success(t("coursewareAgent.visual.completed"));
            else if (state.status === "completed_with_errors") toast.error(t("coursewareAgent.visual.completedWithErrors"));
            else toast.error(t("coursewareAgent.visual.failedRetry"));
          }
        } catch {
          window.clearInterval(timer);
          visualTimerRef.current = null;
          setVisualRunning(false);
        }
      }, 1200);
      visualTimerRef.current = timer;
    } catch (error) {
      setVisualRunning(false);
      toast.error(getApiErrorMessage(error, t("coursewareAgent.visual.failed")));
    }
  };

  const saveVisualSelection = async (page: PptPage, ids: string[]) => {
    const project = activeRef.current;
    if (!project) return;
    try {
      const { data } = await pptApi.saveVisualSelection(project.id, page.id, ids);
      setPages((items) => items.map((item) => item.id === data.id ? data : item));
      toast.success(t("coursewareAgent.visual.selectionSaved"));
    } catch (error) {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.visual.selectionSaveFailed")));
    }
  };

  const generation = usePptGeneration({
    projectId: active?.id,
    pageCount: pages.length,
    onComplete: async () => {
      await refresh();
      setSelected(0);
      setSurface("editor");
    },
  });

  const generateDeck = (themeId?: string) => {
    const project = activeRef.current;
    if (!project || generation.running) return;
    if (themeId && themeId !== project.theme_id) {
      setSurface("layouting");
      void (async () => {
        try {
          const { data } = await pptApi.selectTheme(project.id, themeId);
          setActive(data);
          void generation.generate();
        } catch (error) {
          setSurface("theme");
          toast.error(getApiErrorMessage(error, t("coursewareAgent.theme.saveFailed")));
        }
      })();
      return;
    }
    setSurface("layouting");
    void generation.generate();
  };

  const autosave = usePptAutosave({
    projectId: active?.id,
    save: async (pending) => (await pptApi.patchDocument(pending.projectId, pending.pageId, pending.document, pending.revision)).data,
    onSaved: (data) => setPages((items) => items.map((item) => item.id === data.id ? data : item)),
    onError: (error) => {
      toast.error(getApiErrorMessage(error, t("coursewareAgent.editor.saveFailed")));
      void refresh();
    },
  });

  const exportDeck = async () => {
    const project = activeRef.current;
    if (!project || exportState === "exporting") return;
    setExportState("exporting");
    try {
      const { data } = await pptApi.export(project.id);
      toast.success(t("coursewareAgent.workspace.exportStarted"));
      exportPollRef.current = window.setInterval(async () => {
        try {
          const status = await pptApi.exportStatus(project.id, data.id);
          if (status.data.status === "completed") {
            if (exportPollRef.current) window.clearInterval(exportPollRef.current);
            exportPollRef.current = null;
            setExportState("idle");
            const response = await pptApi.downloadExport(project.id, data.id);
            const url = URL.createObjectURL(response.data);
            const link = document.createElement("a");
            link.href = url;
            link.download = "courseware.pptx";
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.setTimeout(() => URL.revokeObjectURL(url), 1000);
          } else if (status.data.status === "failed") {
            if (exportPollRef.current) window.clearInterval(exportPollRef.current);
            exportPollRef.current = null;
            setExportState("idle");
            toast.error(status.data.error || t("coursewareAgent.workspace.exportFailed"));
          }
        } catch {
          /* polling stays authoritative; transient failures retry */
        }
      }, 1500);
    } catch (error) {
      setExportState("idle");
      toast.error(getApiErrorMessage(error, t("coursewareAgent.workspace.exportFailed")));
    }
  };

  const updateRequirement = (response: RequirementChatResponse) => {
    const project = activeRef.current;
    setRequirement((current) => ({ ...(current || EMPTY_REQUIREMENT(project?.id || "")), ...response, answers: response.answers ?? current?.answers ?? {} }));
  };

  const actions: StudioActions = {
    navigate: setSurface,
    goHome: () => navigate("/teacher/courseware-agent"),
    selectPage: (index) => setSelected(Math.max(0, Math.min(index, pages.length - 1))),
    refresh,
    refreshMessages,
    generateOutline: () => void generateOutline(),
    confirmOutline: () => void confirmOutline(),
    reorderPages: (ids) => void reorderPages(ids),
    patchPage,
    runVisualResearch: () => void runVisualResearch(),
    saveVisualSelection,
    generateDeck,
    retryDesign: generateDeck,
    scheduleSave: autosave.schedule,
    flushAutosave: autosave.flush,
    exportDeck: () => void exportDeck(),
    uploadFiles: (files) => void uploadFiles(files),
    updateRequirement,
  };

  if (!projectId) {
    return (
      <>
        <StudioHome
          projects={projects}
          loading={projectsLoading}
          error={projectsError}
          creating={creating}
          removingIds={removingIds}
          onCreate={(text, files) => void create(text, files)}
          onOpen={(project) => navigate(`/teacher/courseware-agent/${project.id}`)}
          onDelete={(project) => setDeleteCandidate(project)}
          onRetry={() => void loadProjects()}
        />
        <HKUConfirmDialog
          open={Boolean(deleteCandidate)}
          scope="surface"
          title={t("coursewareAgent.home.deleteTitle")}
          description={deleteCandidate ? t("coursewareAgent.home.deleteDescription", { title: deleteCandidate.title }) : undefined}
          icon={<StudioIcon name="trash" size={18} />}
          confirmLabel={t("coursewareAgent.home.deleteConfirm")}
          onClose={() => { if (!deletingId) setDeleteCandidate(null); }}
          onConfirm={confirmRemoveProject}
          loading={Boolean(deletingId)}
        />
      </>
    );
  }

  if (projectLoading || !active) {
    return (
      <div className="st-loading" role="status" aria-live="polite">
        <span className="st-loading-mark" aria-hidden="true"><StudioIcon name="sparkle" size={20} /></span>
        <p>{t("coursewareAgent.project.loading")}</p>
        <div className="st-loading-bar"><i /></div>
      </div>
    );
  }

  const model: StudioModel = {
    project: active,
    pages,
    selected,
    messages,
    requirement,
    sources,
    themes,
    surface,
    outlineGenerating,
    visualRunning,
    layout: { running: generation.running, progress: generation.progress, error: generation.error },
    exportState,
    autosaveSaving: autosave.saving,
    actions,
  };

  return <StudioWorkspace model={model} />;
}
