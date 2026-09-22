import React from "react";
import { Outlet } from "react-router-dom";
import { useAuth } from "../../store";
import WorkspaceSidebar, { readSidebarCollapsed, SidebarItem, writeSidebarCollapsed } from "../../shared/components/WorkspaceSidebar";
import SiteHeader from "./SiteHeader";

export default function Shell() {
  const { user } = useAuth();
  const [sidebarCollapsed, setSidebarCollapsed] = React.useState(readSidebarCollapsed);
  const toggleSidebar = () => setSidebarCollapsed((collapsed) => {
    const next = !collapsed;
    writeSidebarCollapsed(next);
    return next;
  });
  const links: SidebarItem[] = [
    { to: user?.role === "teacher" ? "/teacher" : "/", label: "总览", roles: ["teacher", "student", "admin"], icon: "overview" },
    { to: "/courses", label: user?.role === "teacher" ? "我的课程" : "课程", roles: ["teacher", "student", "admin"], icon: "courses" },
    { to: "/teacher/courseware-agent", label: "PPT Agent", roles: ["teacher"], icon: "courseware" },
    { to: "/teacher/lesson-plan-agent", label: "学案 Agent", roles: ["teacher"], icon: "lessonPlan" },
    { to: "/teacher/ai-video", label: "AI 教学视频", roles: ["teacher"], icon: "video" },
    { to: "/courseware-agent", label: "AI 讲师", roles: ["student"], icon: "ai" },
    { to: "/admin", label: "管理后台", roles: ["admin"], icon: "admin" },
  ];

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
      <SiteHeader />
      <WorkspaceSidebar userRole={user?.role} links={links} collapsed={sidebarCollapsed} onToggle={toggleSidebar} />
      <div className="content"><Outlet /></div>
    </div>
  );
}

