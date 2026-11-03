import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Markdown } from "./Markdown";

describe("shared Markdown", () => {
  it("renders headings, lists, tables and callouts", () => {
    const text = "### 小标题\n- 要点一\n- 要点二\n\n| 量 | 单位 |\n| --- | --- |\n| 力 | N |\n\n> [!tip] 提示\n> 注意单位。";
    const markup = renderToStaticMarkup(<Markdown text={text} />);
    expect(markup).toContain("<h4>小标题</h4>");
    expect(markup).toContain("<ul>");
    expect(markup).toContain("<table>");
    expect(markup).toContain("md-callout-tip");
  });

  it("hides answer callouts when requested", () => {
    const markup = renderToStaticMarkup(<Markdown text={"> [!answer] 参考答案\n> a = 2"} hideAnswers />);
    expect(markup).toBe("");
  });

  it("keeps answer callouts visible by default", () => {
    const markup = renderToStaticMarkup(<Markdown text={"> [!answer] 参考答案\n> a = 2"} />);
    expect(markup).toContain("参考答案");
  });

  it("never injects raw HTML", () => {
    const markup = renderToStaticMarkup(<Markdown text={"<script>alert(1)</script> **safe**"} />);
    expect(markup).not.toContain("<script>");
    expect(markup).toContain("&lt;script&gt;");
    expect(markup).toContain("<strong>safe</strong>");
  });
});
