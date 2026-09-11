import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Breadcrumbs, { buildBreadcrumbs } from "./Breadcrumbs";

describe("buildBreadcrumbs", () => {
  it("builds the course detail hierarchy", () => {
    expect(buildBreadcrumbs("/courses/course-42?tab=assignments")).toEqual([
      { label: "课程", href: "/courses" },
      { label: "课程详情" },
    ]);
  });

  it("builds nested live-class and grading paths", () => {
    expect(buildBreadcrumbs("/courses/course-42/live").map(({ label }) => label)).toEqual(["课程", "课程详情", "直播课堂"]);
    expect(buildBreadcrumbs("/assignments/assignment-7/grading")).toEqual([
      { label: "作业", href: "/assignments" },
      { label: "作业批改" },
    ]);
  });

  it("builds the PPT project hierarchy and normalizes trailing slashes", () => {
    expect(buildBreadcrumbs("/teacher/courseware-agent/project-9/")).toEqual([
      { label: "PPT Agent", href: "/teacher/courseware-agent" },
      { label: "项目工作区" },
    ]);
  });
});

describe("Breadcrumbs", () => {
  it("renders parent links and marks the current page", () => {
    const markup = renderToStaticMarkup(
      <MemoryRouter initialEntries={["/courses/course-42/live?meetingId=demo"]}>
        <Breadcrumbs />
      </MemoryRouter>,
    );
    expect(markup).toContain('href="/courses"');
    expect(markup).toContain('href="/courses/course-42"');
    expect(markup).toContain('aria-current="page"');
    expect(markup).toContain("直播课堂");
  });
});
