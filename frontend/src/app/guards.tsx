import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { Role } from "../api";
import { useAuth } from "../store";
import Shell from "./components/Shell";

export function Protected() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="loading-screen">正在恢复登录状态…</div>;
  return user ? <Shell /> : <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
}

export function RoleGate({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) return <Navigate to={user?.role === "student" ? "/student" : user?.role === "teacher" ? "/teacher" : "/admin"} replace />;
  return <>{children}</>;
}

export function HomeRoute() {
  const { user } = useAuth();
  return <Navigate to={user?.role === "student" ? "/student" : user?.role === "teacher" ? "/teacher" : "/admin"} replace />;
}

