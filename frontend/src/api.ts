import axios from "axios";

export const api = axios.create({ baseURL: "/api", withCredentials: true });
export type Role = "teacher" | "student" | "admin";
export const SUPPORTED_ROLES: Role[] = ["teacher", "student", "admin"];
export type User = { id: string; username: string; email: string; name: string; avatar_url: string | null; role: Role };
export type Course = { id: string; code: string; name: string; description: string; teacher_id: string; teacher_name: string; enrolled_count: number; schedules: { weekday: number; start_time: string; end_time: string; room: string }[] };
