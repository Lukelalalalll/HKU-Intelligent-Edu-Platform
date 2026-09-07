import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import DiscussionModule from "./DiscussionModule";
import { courseSidebarItems } from "./LiveClassPanel";

describe("course discussion module", () => {
  it("exposes the discussion composer and removes Panopto from course navigation", () => {
    const markup = renderToStaticMarkup(<DiscussionModule courseId="course-1" />);
    expect(markup).toContain("COURSE DISCUSSION");
    expect(markup).toContain("发布评论");
    expect(courseSidebarItems).toContain("Discussions");
    expect(courseSidebarItems).not.toContain("Panopto Recordings");
  });
});
