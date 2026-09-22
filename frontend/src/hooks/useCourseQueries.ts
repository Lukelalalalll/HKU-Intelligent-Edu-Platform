import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assignmentsApi, api, courseMaterialsApi, type Assignment, type Course, type CourseChapter, type MaterialKind } from "../api";
import { queryKeys } from "../queryClient";

export function useCoursesQuery() {
  return useQuery({ queryKey: queryKeys.courses, queryFn: async ({ signal }) => (await api.get<Course[]>("/courses", { signal })).data });
}

export function useCourseQuery(id?: string) {
  return useQuery({ queryKey: queryKeys.course(id || ""), queryFn: async ({ signal }) => (await api.get<Course>(`/courses/${id}`, { signal })).data, enabled: Boolean(id) });
}

export function useMaterialsQuery(courseId?: string, kind?: MaterialKind) {
  return useQuery({ queryKey: queryKeys.materials(courseId || "", kind || ""), queryFn: async ({ signal }) => (await courseMaterialsApi.list(courseId!, kind!, { signal } as never)).data, enabled: Boolean(courseId && kind) });
}

export function useAssignmentsQuery(courseId?: string) {
  return useQuery({ queryKey: queryKeys.assignments(courseId || ""), queryFn: async ({ signal }) => (await assignmentsApi.list(courseId!, { signal } as never)).data, enabled: Boolean(courseId) });
}

export function useCreateAssignmentMutation(courseId: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (payload: Parameters<typeof assignmentsApi.create>[1]) => assignmentsApi.create(courseId, payload), onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.assignments(courseId) }) });
}
