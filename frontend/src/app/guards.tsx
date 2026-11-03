/**
 * Route guards that bridge the auth store with React Router redirects.
 */
import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import type { Role } from "../api";
import { useAuth } from "../store";
import Shell from "./components/Shell";

/**
 * Render the shell for signed-in users or redirect to login.
 */
export function Protected() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="loading-screen">正在恢复登录状态…</div>;
  return user ? <Shell /> : <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
}

/**
 * Restrict a subtree to the given roles and bounce others to their home.
 */
export function RoleGate({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user || !roles.includes(user.role)) return <Navigate to={user?.role === "student" ? "/student" : user?.role === "teacher" ? "/teacher" : "/admin"} replace />;
  return <>{children}</>;
}

/**
 * Send each role to its own landing route.
 */
export function HomeRoute() {
  const { user } = useAuth();
  return <Navigate to={user?.role === "student" ? "/student" : user?.role === "teacher" ? "/teacher" : "/admin"} replace />;
}

