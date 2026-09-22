import { useQuery } from "@tanstack/react-query";
import { api, type StudentDashboardData, type TeacherDashboardData } from "../api";
import { queryKeys } from "../queryClient";

export function useTeacherDashboardQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboard.teacher,
    queryFn: async ({ signal }) => (await api.get<TeacherDashboardData>("/teacher/dashboard", { signal })).data,
    enabled,
  });
}

export function useStudentDashboardQuery(enabled = true) {
  return useQuery({
    queryKey: queryKeys.dashboard.student,
    queryFn: async ({ signal }) => (await api.get<StudentDashboardData>("/student/dashboard", { signal })).data,
    enabled,
  });
}
