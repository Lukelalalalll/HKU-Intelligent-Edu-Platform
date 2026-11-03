/**
 * Lesson plan agent route container.
 *
 * The home surface owns project discovery and creation; a project route hands
 * off to the workspace, which loads its own state.
 */
import React, { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { useNavigate, useParams } from "react-router-dom";
import { getApiErrorMessage, lessonPlanApi, type LessonPlanCapabilities, type LessonPlanProject } from "../../api";
import { useI18n } from "../../i18n";
import { HKUConfirmDialog } from "../../shared/components/HKUDialog";
import LessonPlanHome from "./LessonPlanHome";
import LessonPlanWorkspace from "./LessonPlanWorkspace";
import "./LessonPlanAgentRoute.css";

/** Entry point for the lesson plan agent feature. */
export default function LessonPlanAgentRoute() {
  const { projectId } = useParams<{ projectId?: string }>();
  const navigate = useNavigate();
  const { t } = useI18n();
  const [projects, setProjects] = useState<LessonPlanProject[]>([]);
  const [capabilities, setCapabilities] = useState<LessonPlanCapabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [creating, setCreating] = useState(false);
  const [deleteCandidate, setDeleteCandidate] = useState<LessonPlanProject | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadProjects = useCallback(async () => {
    setLoading(true);
    try {
      const [list, caps] = await Promise.all([lessonPlanApi.projects(), lessonPlanApi.capabilities()]);
      setProjects(list.data.items);
      setCapabilities(caps.data);
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!projectId) void loadProjects();
  }, [loadProjects, projectId]);

  const createProject = useCallback(
    async (text: string, files: File[]) => {
      if (creating) return;
      setCreating(true);
      try {
        const fallbackTitle = files[0]?.name.replace(/\.[^.]+$/, "").slice(0, 40) || "";
        const { data } = await lessonPlanApi.createProject({ title: text.slice(0, 40) || fallbackTitle, request_text: text });
        let uploaded = 0;
        for (const file of files) {
          try {
            await lessonPlanApi.upload(data.id, file);
            uploaded += 1;
          } catch (uploadError: unknown) {
            toast.error(getApiErrorMessage(uploadError, t("lessonPlan.toast.uploadFailed", { name: file.name })));
          }
        }
        if (uploaded) toast.success(t(uploaded === 1 ? "lessonPlan.toast.uploadSuccess.one" : "lessonPlan.toast.uploadSuccess.other", { count: uploaded }));
        navigate(`/teacher/lesson-plan-agent/${data.id}`);
      } catch (createError: unknown) {
        toast.error(getApiErrorMessage(createError, t("lessonPlan.toast.createFailed")));
      } finally {
        setCreating(false);
      }
    },
    [creating, navigate, t],
  );

  const confirmDelete = useCallback(async () => {
    if (!deleteCandidate || deleting) return;
    setDeleting(true);
    try {
      await lessonPlanApi.deleteProject(deleteCandidate.id);
      setProjects((items) => items.filter((item) => item.id !== deleteCandidate.id));
      setDeleteCandidate(null);
      toast.success(t("lessonPlan.toast.deleted"));
    } catch (deleteError: unknown) {
      toast.error(getApiErrorMessage(deleteError, t("lessonPlan.toast.deleteFailed")));
    } finally {
      setDeleting(false);
    }
  }, [deleteCandidate, deleting, t]);

  if (projectId) return <LessonPlanWorkspace projectId={projectId} />;

  return (
    <>
      <LessonPlanHome
        projects={projects}
        loading={loading}
        error={error}
        creating={creating}
        capabilities={capabilities}
        onRetry={() => void loadProjects()}
        onCreate={(text, files) => void createProject(text, files)}
        onOpen={(project) => navigate(`/teacher/lesson-plan-agent/${project.id}`)}
        onDelete={setDeleteCandidate}
      />
      <HKUConfirmDialog
        open={Boolean(deleteCandidate)}
        onClose={() => setDeleteCandidate(null)}
        onConfirm={() => void confirmDelete()}
        title={t("lessonPlan.dialog.deleteTitle")}
        description={t("lessonPlan.dialog.deleteBody", { title: deleteCandidate?.title || "" })}
        confirmLabel={t("lessonPlan.dialog.deleteConfirm")}
        loading={deleting}
      />
    </>
  );
}
