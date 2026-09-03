import React from "react";
import { Link, useLocation } from "react-router-dom";

export type BreadcrumbItem = {
  label: string;
  href?: string;
};

const normalizePath = (pathname: string) => {
  const path = pathname.split("?")[0].split("#")[0].replace(/\/{2,}/g, "/").replace(/\/$/, "");
  return path || "/";
};

const segment = (value: string) => encodeURIComponent(decodeURIComponent(value));

/**
 * Keeps breadcrumb semantics independent from the rendered header so route
 * coverage can be tested without mounting the whole application shell.
 */
export function buildBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const path = normalizePath(pathname);

  if (path === "/" || path === "/student" || path === "/teacher") {
    return [{ label: "总览" }];
  }
  if (path === "/courses") {
    return [{ label: "课程" }];
  }
  if (path.startsWith("/courses/")) {
    const [, , rawCourseId, child] = path.split("/");
    const courseHref = `/courses/${segment(rawCourseId || "")}`;
    if (child === "live") {
      return [
        { label: "课程", href: "/courses" },
        { label: "课程详情", href: courseHref },
        { label: "直播课堂" },
      ];
    }
    return [{ label: "课程", href: "/courses" }, { label: "课程详情" }];
  }
  if (path === "/assignments") {
    return [{ label: "作业" }];
  }
  if (path.startsWith("/assignments/") && path.endsWith("/grading")) {
    return [{ label: "作业", href: "/assignments" }, { label: "作业批改" }];
  }
  if (path === "/teacher/courseware-agent") {
    return [{ label: "课件 Agent" }];
  }
  if (path.startsWith("/teacher/courseware-agent/")) {
    return [{ label: "课件 Agent", href: "/teacher/courseware-agent" }, { label: "项目工作区" }];
  }
  if (path === "/admin") {
    return [{ label: "管理后台" }];
  }
  if (path === "/profile") {
    return [{ label: "个人资料" }];
  }

  return [{ label: "总览", href: "/" }, { label: "当前页面" }];
}

export default function Breadcrumbs() {
  const { pathname } = useLocation();
  const items = buildBreadcrumbs(pathname);

  return (
    <nav className="breadcrumbs" aria-label="当前位置">
      <ol>
        {items.map((item, index) => {
          const current = index === items.length - 1;
          return (
            <React.Fragment key={`${item.label}-${index}`}>
              {index > 0 && <li className="breadcrumb-separator" aria-hidden="true">/</li>}
              <li className={`breadcrumb-item ${current ? "is-current" : ""}`}>
                {item.href && !current ? (
                  <Link to={item.href}>
                    {index === 0 && <span className="breadcrumb-mark" aria-hidden="true">✦</span>}
                    <span>{item.label}</span>
                  </Link>
                ) : (
                  <span aria-current={current ? "page" : undefined}>
                    {index === 0 && <span className="breadcrumb-mark" aria-hidden="true">✦</span>}
                    <span>{item.label}</span>
                  </span>
                )}
              </li>
            </React.Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
