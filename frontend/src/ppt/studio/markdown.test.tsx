import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { Markdown, renderInline } from "./markdown";

describe("Markdown", () => {
  it("renders inline emphasis and code", () => {
    const markup = renderToStaticMarkup(<Markdown text={"Use **bold**, *italic* and `code`."} />);
    expect(markup).toContain("<strong>bold</strong>");
    expect(markup).toContain("<em>italic</em>");
    expect(markup).toContain("<code>code</code>");
  });

  it("renders bullet and numbered lists as lists", () => {
    const markup = renderToStaticMarkup(<Markdown text={"Intro\n- one\n- two\n1. first\n2. second"} />);
    expect(markup).toContain("<ul>");
    expect(markup).toContain("<ol>");
    expect(markup.match(/<li>/g)?.length).toBe(4);
  });

  it("never injects raw HTML from the model", () => {
    const markup = renderToStaticMarkup(<Markdown text={"<b>not bold</b> and <script>alert(1)</script>"} />);
    expect(markup).not.toContain("<b>");
    expect(markup).not.toContain("<script>");
    expect(markup).toContain("&lt;b&gt;");
  });

  it("returns inline nodes for plain strings", () => {
    expect(renderInline("plain text", "k")).toEqual(["plain text"]);
  });

  it("renders nothing for empty input", () => {
    expect(renderToStaticMarkup(<Markdown text={""} />)).toBe("");
  });
});
