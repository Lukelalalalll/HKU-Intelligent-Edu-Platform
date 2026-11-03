import React from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useI18n } from "../../i18n";
import { useAuth } from "../../store";
import WorkspaceSidebar, { readSidebarCollapsed, SidebarItem, writeSidebarCollapsed } from "../../shared/components/WorkspaceSidebar";
import SiteHeader from "./SiteHeader";

/**
 * Authenticated shell: fixed header, workspace sidebar and routed content.
 *
 * The courseware studio owns its own full-height canvas; on a project route the
 * global sidebar collapses away so the studio keeps a single navigation layer.
 */
export default function Shell() {
  const { user } = useAuth();
  const { t } = useI18n();
  const location = useLocation();
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(readSidebarCollapsed);
  const toggleSidebar = () => setSidebarCollapsed((collapsed) => {
    const next = !collapsed;
    writeSidebarCollapsed(next);
    return next;
  });
  // Both teacher agents own a full-height workspace on their project routes.
  const isStudio = location.pathname.startsWith("/teacher/courseware-agent") || location.pathname.startsWith("/teacher/lesson-plan-agent");
  const isStudioFocus = /^\/teacher\/(?:courseware-agent|lesson-plan-agent)\/[^/]+\/?$/.test(location.pathname);
  const links: SidebarItem[] = [
    { to: user?.role === "teacher" ? "/teacher" : "/", label: t("common.nav.overview"), roles: ["teacher", "student", "admin"], icon: "overview" },
    { to: "/courses", label: user?.role === "teacher" ? t("common.nav.myCourses") : t("common.nav.courses"), roles: ["teacher", "student", "admin"], icon: "courses" },
    { to: "/teacher/courseware-agent", label: t("common.nav.coursewareAgent"), roles: ["teacher"], icon: "courseware" },
    { to: "/teacher/lesson-plan-agent", label: t("common.nav.lessonPlanAgent"), roles: ["teacher"], icon: "lessonPlan" },
    { to: "/teacher/ai-video", label: t("common.nav.teachingVideo"), roles: ["teacher"], icon: "video" },
    { to: "/courseware-agent", label: t("common.nav.aiLecturer"), roles: ["student"], icon: "ai" },
    { to: "/admin", label: t("common.nav.admin"), roles: ["admin"], icon: "admin" },
  ];

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""} ${isStudio ? "is-studio" : ""} ${isStudioFocus ? "is-studio-focus" : ""}`}>
      <SiteHeader />
      <WorkspaceSidebar userRole={user?.role} links={links} collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
      <div className={`content ${isStudio ? "content--studio" : ""}`.trim()}><Outlet /></div>
    </div>
  );
}
