import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, teacherVideoApi, type Course, type VideoGenerationJob } from "../api";
import { queryKeys } from "../queryClient";

const terminalStatuses = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);

export function useVideoProjectQuery(id?: string) {
  return useQuery({
    queryKey: queryKeys.videoProject(id || ""),
    queryFn: async ({ signal }) => (await teacherVideoApi.getProject(id!, { signal })).data,
    enabled: Boolean(id),
  });
}

export function useVideoProjectsQuery() {
  return useQuery({
    queryKey: queryKeys.videoProjects,
    queryFn: async ({ signal }) => (await teacherVideoApi.listProjects({ signal })).data,
  });
}

export function useCoursesForVideoQuery() {
  return useQuery({
    queryKey: queryKeys.courses,
    queryFn: async ({ signal }) => (await api.get<Course[]>("/courses", { signal })).data,
  });
}

export function useVideoScenesQuery(id?: string) {
  return useQuery({
    queryKey: [...queryKeys.videoProject(id || ""), "scenes"],
    queryFn: async ({ signal }) => (await teacherVideoApi.scenes(id!, { signal })).data,
    enabled: Boolean(id),
  });
}

export function useVideoJobsQuery(id?: string) {
  return useQuery({
    queryKey: queryKeys.videoJobs(id || ""),
    queryFn: async ({ signal }) => (await teacherVideoApi.jobs(id!, { signal })).data,
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const jobs = query.state.data as VideoGenerationJob[] | undefined;
      return jobs?.some((job) => !terminalStatuses.has(job.status)) ? 2_000 : false;
    },
  });
}

export function useVideoJobActions(projectId: string, job?: VideoGenerationJob | null) {
  const client = useQueryClient();
  const update = (data: VideoGenerationJob) => {
    client.setQueryData<VideoGenerationJob[]>(queryKeys.videoJobs(projectId), (jobs) => jobs?.map((item) => item.id === data.id ? data : item) ?? [data]);
  };
  const cancel = useMutation({ mutationFn: () => job ? teacherVideoApi.cancelJob(projectId, job.id) : Promise.reject(new Error("没有可取消的任务")), onSuccess: ({ data }) => update(data) });
  const retry = useMutation({ mutationFn: () => job ? teacherVideoApi.retryJob(projectId, job.id) : Promise.reject(new Error("没有可重试的任务")), onSuccess: ({ data }) => update(data) });
  return { cancel, retry };
}

export function useVideoProjectMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => teacherVideoApi.patchProject(id, payload),
    onSuccess: (_, variables) => { void client.invalidateQueries({ queryKey: queryKeys.videoProject(variables.id) }); },
  });
}
