import React from "react";
import { NavLink } from "react-router-dom";
import type { Role } from "../../api";

export type SidebarIconName = "overview" | "courses" | "assignments" | "courseware" | "admin" | "profile" | "collapse" | "expand";

export type SidebarItem = {
  to: string;
  label: string;
  roles: Role[];
  icon: SidebarIconName;
  end?: boolean;
};

type WorkspaceSidebarProps = {
  userRole?: Role;
  links: SidebarItem[];
  collapsed: boolean;
  onToggle: () => void;
};

export const SIDEBAR_STORAGE_KEY = "hku-sidebar-collapsed";

export function readSidebarCollapsed(storage?: Pick<Storage, "getItem">): boolean {
  const source = storage ?? (typeof window !== "undefined" ? window.localStorage : undefined);
  return source?.getItem(SIDEBAR_STORAGE_KEY) === "1";
}

export function writeSidebarCollapsed(collapsed: boolean, storage?: Pick<Storage, "setItem">): void {
  const target = storage ?? (typeof window !== "undefined" ? window.localStorage : undefined);
  target?.setItem(SIDEBAR_STORAGE_KEY, collapsed ? "1" : "0");
}

const iconPaths: Record<SidebarIconName, string[]> = {
  overview: ["M4 13h6V4H4v9Zm0 7h6v-4H4v4Zm10 0h6v-9h-6v9Zm0-16v4h6V4h-6Z"],
  courses: ["M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5v-15Z", "M4 20.5A2.5 2.5 0 0 1 6.5 18H20"],
  assignments: ["m6 4 1.5 1.5L10 3l2.5 2.5L15 3l2.5 2.5L19 4v16H6V4Z", "m9 12 2 2 4-4"],
  courseware: ["M12 3 14.1 9.1 21 12l-6.9 2.9L12 21l-2.1-6.1L3 12l6.9-2.9L12 3Z", "M19 3v4m2-2h-4"],
  admin: ["M12 3 20 6v5c0 5.2-3.4 8.2-8 10-4.6-1.8-8-4.8-8-10V6l8-3Z", "m9 12 2 2 4-4"],
  profile: ["M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z", "M4 21a8 8 0 0 1 16 0"],
  collapse: ["m15 18-6-6 6-6", "M9 12h11"],
  expand: ["m9 18 6-6-6-6", "M4 12h11"],
};

export function SidebarIcon({ name }: { name: SidebarIconName }) {
  return (
    <svg className="sidebar-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {iconPaths[name].map((path, index) => <path key={`${name}-${index}`} d={path} fill={path.startsWith("M4 13") ? "currentColor" : undefined} />)}
    </svg>
  );
}

export default function WorkspaceSidebar({ userRole, links, collapsed, onToggle }: WorkspaceSidebarProps) {
  const visibleLinks = links.filter((link) => userRole && link.roles.includes(userRole));
  return (
    <aside className="workspace-sidebar" data-sidebar-mode={collapsed ? "collapsed" : "expanded"}>
      <button className="sidebar-toggle" type="button" onClick={onToggle} aria-label={collapsed ? "展开侧栏" : "收起侧栏"} title={collapsed ? "展开侧栏" : "收起侧栏"}>
        <SidebarIcon name={collapsed ? "expand" : "collapse"} />
        <span className="nav-label">{collapsed ? "展开侧栏" : "收起侧栏"}</span>
      </button>
      <nav className="sidebar-nav" aria-label="工作台导航">
        {visibleLinks.map((link) => (
          <NavLink key={link.to} to={link.to} end={link.end ?? (link.to === "/" || link.to === "/teacher")} title={link.label}>
            <SidebarIcon name={link.icon} />
            <span className="nav-label">{link.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-footer">
        <NavLink to="/profile" end title="个人资料">
          <SidebarIcon name="profile" />
          <span className="nav-label">个人资料</span>
        </NavLink>
      </div>
    </aside>
  );
}
