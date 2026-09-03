import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import WorkspaceSidebar, { readSidebarCollapsed, SidebarItem, writeSidebarCollapsed } from "./WorkspaceSidebar";

const links: SidebarItem[] = [
  { to: "/teacher", label: "总览", roles: ["teacher"], icon: "overview" },
  { to: "/courses", label: "课程", roles: ["teacher", "student"], icon: "courses" },
  { to: "/admin", label: "管理后台", roles: ["admin"], icon: "admin" },
];

const renderSidebar = (collapsed: boolean, userRole: "teacher" | "student" | "admin") => renderToStaticMarkup(
  <MemoryRouter>
    <WorkspaceSidebar userRole={userRole} links={links} collapsed={collapsed} onToggle={() => undefined} />
  </MemoryRouter>,
);

describe("WorkspaceSidebar", () => {
  it("keeps local SVG icons available when collapsed", () => {
    const markup = renderSidebar(true, "teacher");
    expect(markup).toContain('data-sidebar-mode="collapsed"');
    expect(markup.match(/class="sidebar-icon"/g)).toHaveLength(4);
    expect(markup).toContain('title="总览"');
  });

  it("filters navigation items by role", () => {
    const markup = renderSidebar(false, "student");
    expect(markup).toContain("课程");
    expect(markup).not.toContain("管理后台");
  });

  it("round-trips the collapsed preference without requiring a browser global", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => values.set(key, value),
    };
    expect(readSidebarCollapsed(storage)).toBe(false);
    writeSidebarCollapsed(true, storage);
    expect(readSidebarCollapsed(storage)).toBe(true);
  });
});
