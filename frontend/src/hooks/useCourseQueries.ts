import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { assignmentsApi, api, courseMaterialsApi, liveClassApi, participantApi, type Assignment, type Course, type CourseChapter, type LiveClass, type MaterialKind, type Participant } from "../api";
import { queryKeys } from "../queryClient";

/**
 * List the courses visible to the signed-in user.
 */
export function useCoursesQuery() {
  return useQuery({ queryKey: queryKeys.courses, queryFn: async ({ signal }) => (await api.get<Course[]>("/courses", { signal })).data });
}

/**
 * Load one course by id.
 */
export function useCourseQuery(id?: string) {
  return useQuery({ queryKey: queryKeys.course(id || ""), queryFn: async ({ signal }) => (await api.get<Course>(`/courses/${id}`, { signal })).data, enabled: Boolean(id) });
}

/**
 * Load chapters of one material kind.
 */
export function useMaterialsQuery(courseId?: string, kind?: MaterialKind) {
  return useQuery({ queryKey: queryKeys.materials(courseId || "", kind || ""), queryFn: async ({ signal }) => (await courseMaterialsApi.list(courseId!, kind!, { signal } as never)).data, enabled: Boolean(courseId && kind) });
}

/**
 * Load live-class state and refresh it every 30 seconds.
 */
export function useLiveClassQuery(courseId?: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.liveClass(courseId || ""),
    queryFn: async ({ signal }) => (await liveClassApi.get(courseId!, { signal })).data,
    enabled: Boolean(courseId) && enabled,
    refetchInterval: 30_000,
  });
}

/**
 * List the participants of a course.
 */
export function useParticipantsQuery(courseId?: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.participants(courseId || ""),
    queryFn: async ({ signal }) => (await participantApi.list(courseId!, { signal })).data,
    enabled: Boolean(courseId) && enabled,
  });
}

/**
 * List the assignments of a course.
 */
export function useCourseAssignmentsQuery(courseId?: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.assignments(courseId || ""),
    queryFn: async ({ signal }) => (await assignmentsApi.list(courseId!, { signal })).data,
    enabled: Boolean(courseId) && enabled,
  });
}

/**
 * Provision Zoom meetings and seed the cached live-class state.
 */
export function useProvisionLiveClassMutation(courseId: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => liveClassApi.provision(courseId),
    onSuccess: ({ data }) => client.setQueryData<LiveClass>(queryKeys.liveClass(courseId), data),
  });
}

/**
 * Expose a material-cache invalidation callback.
 */
export function useCourseMaterialsMutation(courseId: string, kind: MaterialKind) {
  const client = useQueryClient();
  const invalidate = () => client.invalidateQueries({ queryKey: queryKeys.materials(courseId, kind) });
  return { invalidate };
}

/**
 * List assignments for a course id.
 */
export function useAssignmentsQuery(courseId?: string) {
  return useQuery({ queryKey: queryKeys.assignments(courseId || ""), queryFn: async ({ signal }) => (await assignmentsApi.list(courseId!, { signal } as never)).data, enabled: Boolean(courseId) });
}

/**
 * Create an assignment and invalidate the course list.
 */
export function useCreateAssignmentMutation(courseId: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (payload: Parameters<typeof assignmentsApi.create>[1]) => assignmentsApi.create(courseId, payload), onSuccess: () => client.invalidateQueries({ queryKey: queryKeys.assignments(courseId) }) });
}
