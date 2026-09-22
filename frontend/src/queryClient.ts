import { QueryClient } from "@tanstack/react-query";
import { toApiError } from "./lib/apiClient";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        const normalized = toApiError(error);
        return normalized.retryable && failureCount < 2;
      },
    },
    mutations: { retry: 0 },
  },
});

export const queryKeys = {
  dashboard: {
    teacher: ["dashboard", "teacher"] as const,
    student: ["dashboard", "student"] as const,
  },
  courses: ["courses"] as const,
  course: (id: string) => ["courses", id] as const,
  materials: (courseId: string, kind: string) => ["materials", courseId, kind] as const,
  assignments: (courseId: string) => ["assignments", courseId] as const,
  liveClass: (courseId: string) => ["courses", courseId, "live-class"] as const,
  participants: (courseId: string) => ["courses", courseId, "participants"] as const,
  videoProjects: ["video-projects"] as const,
  videoProject: (id: string) => ["video-projects", id] as const,
  videoJobs: (id: string) => ["video-projects", id, "jobs"] as const,
};
