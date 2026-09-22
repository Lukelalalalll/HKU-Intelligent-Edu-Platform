import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { teacherVideoApi, type VideoGenerationJob } from "../api";
import { queryKeys } from "../queryClient";

const terminalStatuses = new Set(["completed", "completed_with_errors", "failed", "cancelled"]);

export function useVideoProjectQuery(id?: string) {
  return useQuery({
    queryKey: queryKeys.videoProject(id || ""),
    queryFn: async ({ signal }) => (await teacherVideoApi.getProject(id!, { signal })).data,
    enabled: Boolean(id),
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

export function useVideoProjectMutation() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Record<string, unknown> }) => teacherVideoApi.patchProject(id, payload),
    onSuccess: (_, variables) => { void client.invalidateQueries({ queryKey: queryKeys.videoProject(variables.id) }); },
  });
}
