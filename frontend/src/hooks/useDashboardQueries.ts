import { useQuery } from "@tanstack/react-query";
import { api, type StudentDashboardData, type TeacherDashboardData } from "../api";
import { queryKeys } from "../queryClient";

/**
 * Load the teacher dashboard; disable it for other roles.
 */
export function useTeacherDashboardQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboard.teacher,
    queryFn: async ({ signal }) => (await api.get<TeacherDashboardData>("/teacher/dashboard", { signal })).data,
    enabled,
  });
}

/**
 * Load the student dashboard; disable it for other roles.
 */
export function useStudentDashboardQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboard.student,
    queryFn: async ({ signal }) => (await api.get<StudentDashboardData>("/student/dashboard", { signal })).data,
    enabled,
  });
}
