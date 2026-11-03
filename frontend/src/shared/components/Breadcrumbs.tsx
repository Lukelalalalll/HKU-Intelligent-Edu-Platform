import React from "react";
import { Link, useLocation } from "react-router-dom";
import { createTranslator, DEFAULT_LOCALE, useI18n, type TranslationKey, type Translator } from "../../i18n";

/**
 * One rendered breadcrumb; ``href`` makes it a link unless it is the current page.
 */
export type BreadcrumbItem = {
  label: string;
  href?: string;
};

type BreadcrumbDescriptor = {
  key: TranslationKey;
  href?: string;
};

const normalizePath = (pathname: string) => {
  const path = pathname.split("?")[0].split("#")[0].replace(/\/{2,}/g, "/").replace(/\/$/, "");
  return path || "/";
};

const segment = (value: string) => encodeURIComponent(decodeURIComponent(value));

const defaultTranslator = createTranslator(DEFAULT_LOCALE);

/** Build the route hierarchy as translation keys so it stays locale-agnostic. */
function describeBreadcrumbs(pathname: string): BreadcrumbDescriptor[] {
  const path = normalizePath(pathname);

  if (path === "/" || path === "/student" || path === "/teacher") {
    return [{ key: "common.breadcrumbs.overview" }];
  }
  if (path === "/courses") {
    return [{ key: "common.breadcrumbs.courses" }];
  }
  if (path.startsWith("/courses/")) {
    const [, , rawCourseId, child] = path.split("/");
    const courseHref = `/courses/${segment(rawCourseId || "")}`;
    if (child === "live") {
      return [
        { key: "common.breadcrumbs.courses", href: "/courses" },
        { key: "common.breadcrumbs.courseDetail", href: courseHref },
        { key: "common.breadcrumbs.liveClass" },
      ];
    }
    return [{ key: "common.breadcrumbs.courses", href: "/courses" }, { key: "common.breadcrumbs.courseDetail" }];
  }
  if (path === "/assignments") {
    return [{ key: "common.breadcrumbs.assignments" }];
  }
  if (path.startsWith("/assignments/") && path.endsWith("/grading")) {
    return [{ key: "common.breadcrumbs.assignments", href: "/assignments" }, { key: "common.breadcrumbs.grading" }];
  }
  if (path === "/teacher/courseware-agent") {
    return [{ key: "common.breadcrumbs.coursewareAgent" }];
  }
  if (path.startsWith("/teacher/courseware-agent/")) {
    return [{ key: "common.breadcrumbs.coursewareAgent", href: "/teacher/courseware-agent" }, { key: "common.breadcrumbs.projectWorkspace" }];
  }
  if (path === "/teacher/lesson-plan-agent") {
    return [{ key: "common.breadcrumbs.lessonPlanAgent" }];
  }
  if (path.startsWith("/teacher/lesson-plan-agent/")) {
    return [{ key: "common.breadcrumbs.lessonPlanAgent", href: "/teacher/lesson-plan-agent" }, { key: "common.breadcrumbs.projectWorkspace" }];
  }
  if (path === "/teacher/ai-video") {
    return [{ key: "common.breadcrumbs.teachingVideo" }];
  }
  if (path.startsWith("/teacher/ai-video/")) {
    return [{ key: "common.breadcrumbs.teachingVideo", href: "/teacher/ai-video" }, { key: "common.breadcrumbs.projectWorkspace" }];
  }
  if (path === "/courseware-agent") {
    return [{ key: "common.breadcrumbs.aiLecturer" }];
  }
  if (path === "/admin") {
    return [{ key: "common.breadcrumbs.admin" }];
  }
  if (path === "/profile") {
    return [{ key: "common.breadcrumbs.profile" }];
  }

  return [{ key: "common.breadcrumbs.overview", href: "/" }, { key: "common.breadcrumbs.currentPage" }];
}

/**
 * Keeps breadcrumb semantics independent from the rendered header so route
 * coverage can be tested without mounting the whole application shell.
 *
 * @param pathname Route path to describe.
 * @param t        Translator used to resolve labels; defaults to the source locale.
 */
export function buildBreadcrumbs(pathname: string, t: Translator = defaultTranslator): BreadcrumbItem[] {
  return describeBreadcrumbs(pathname).map(({ key, href }) => ({ label: t(key), href }));
}

/**
 * Route-aware breadcrumb trail rendered by the site header.
 */
export default function Breadcrumbs() {
  const { pathname } = useLocation();
  const { t } = useI18n();
  const items = buildBreadcrumbs(pathname, t);

  return (
    <nav className="breadcrumbs" aria-label={t("common.breadcrumbs.currentLocation")}>
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
