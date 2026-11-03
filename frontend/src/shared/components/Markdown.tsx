/**
 * Minimal Markdown renderer for agent replies and lesson plan pages.
 *
 * Assistant messages and page bodies are written as light Markdown. Rendering
 * happens through React nodes (never `dangerouslySetInnerHTML`), so model or
 * teacher content cannot inject markup. Supported: paragraphs, bullet/numbered
 * lists, headings, tables, blockquotes, `> [!tip]` / `> [!answer]` callouts,
 * horizontal rules, bold, italic and inline code.
 */
import React from "react";

const INLINE_PATTERN = /(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`)/g;
const HEADING_PATTERN = /^(#{1,4})\s+(.*)$/;
const UL_PATTERN = /^[-*+]\s+(.*)$/;
const OL_PATTERN = /^\d+[.)]\s+(.*)$/;
const HR_PATTERN = /^(?:-{3,}|\*{3,}|_{3,})$/;
const TABLE_SEPARATOR = /^\s*\|?[\s:|-]+\|?\s*$/;
const CALLOUT_PATTERN = /^\[!(tip|note|warning|answer)\]\s*(.*)$/i;

/** Split a line into styled inline nodes. */
export function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let lastIndex = 0;
  let index = 0;
  INLINE_PATTERN.lastIndex = 0;
  let match: RegExpExecArray | null = INLINE_PATTERN.exec(text);
  while (match) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${index++}`;
    if (token.startsWith("**")) nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    else if (token.startsWith("`")) nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    else nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    lastIndex = match.index + token.length;
    match = INLINE_PATTERN.exec(text);
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export type MarkdownProps = {
  text?: string | null;
  className?: string;
  /** Hide `> [!answer]` callouts (used for the student-facing print preview). */
  hideAnswers?: boolean;
};

function splitRow(line: string): string[] {
  let raw = line.trim();
  if (raw.startsWith("|")) raw = raw.slice(1);
  if (raw.endsWith("|")) raw = raw.slice(0, -1);
  return raw.split("|").map((cell) => cell.trim());
}

function isTableStart(lines: string[], index: number): boolean {
  return lines[index].includes("|") && index + 1 < lines.length && TABLE_SEPARATOR.test(lines[index + 1].trim());
}

function renderLines(lines: string[], hideAnswers: boolean, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let index = 0;
  let counter = 0;
  const nextKey = (kind: string) => `${keyPrefix}-${kind}-${counter++}`;

  while (index < lines.length) {
    const trimmed = lines[index].trim();
    if (!trimmed) { index += 1; continue; }

    if (trimmed.startsWith("```")) {
      index += 1;
      const code: string[] = [];
      while (index < lines.length && !lines[index].trim().startsWith("```")) { code.push(lines[index]); index += 1; }
      if (index < lines.length) index += 1;
      nodes.push(<pre key={nextKey("pre")}><code>{code.join("\n")}</code></pre>);
      continue;
    }

    const heading = HEADING_PATTERN.exec(trimmed);
    if (heading) {
      const level = Math.min(Math.max(heading[1].length + 1, 2), 4);
      const Tag = `h${level}` as "h2" | "h3" | "h4";
      nodes.push(<Tag key={nextKey("heading")}>{renderInline(heading[2], nextKey("heading-inline"))}</Tag>);
      index += 1;
      continue;
    }

    if (HR_PATTERN.test(trimmed)) {
      nodes.push(<hr key={nextKey("hr")} />);
      index += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const block: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        block.push(lines[index].trim().slice(1).replace(/^\s/, ""));
        index += 1;
      }
      const match = CALLOUT_PATTERN.exec(block[0] ?? "");
      if (match) {
        const tone = match[1].toLowerCase();
        if (tone === "answer" && hideAnswers) continue;
        const label = match[2].trim();
        nodes.push(
          <div className={`md-callout md-callout-${tone}`} key={nextKey("callout")}>
            {label ? <div className="md-callout-label">{label}</div> : null}
            {renderLines(block.slice(1), hideAnswers, nextKey("callout-body"))}
          </div>,
        );
      } else {
        nodes.push(<blockquote key={nextKey("quote")}>{renderLines(block, hideAnswers, nextKey("quote-body"))}</blockquote>);
      }
      continue;
    }

    if (isTableStart(lines, index)) {
      const header = splitRow(lines[index]);
      index += 2;
      const rows: string[][] = [];
      while (index < lines.length && lines[index].trim() && lines[index].includes("|")) {
        rows.push(splitRow(lines[index]));
        index += 1;
      }
      nodes.push(
        <table key={nextKey("table")}>
          <thead><tr>{header.map((cell, cellIndex) => <th key={`${nextKey("th")}-${cellIndex}`}>{renderInline(cell, nextKey("th-inline"))}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`${nextKey("tr")}-${rowIndex}`}>
                {header.map((_, cellIndex) => (
                  <td key={`${nextKey("td")}-${cellIndex}`}>{renderInline(row[cellIndex] ?? "", nextKey("td-inline"))}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>,
      );
      continue;
    }

    const bullet = UL_PATTERN.exec(trimmed);
    const ordered = OL_PATTERN.exec(trimmed);
    if (bullet || ordered) {
      const isOrdered = Boolean(ordered);
      const items: string[] = [];
      while (index < lines.length) {
        const candidate = lines[index].trim();
        const match = isOrdered ? OL_PATTERN.exec(candidate) : UL_PATTERN.exec(candidate);
        if (!match) break;
        items.push(match[1]);
        index += 1;
      }
      const Tag = isOrdered ? "ol" : "ul";
      nodes.push(<Tag key={nextKey("list")}>{items.map((item, itemIndex) => <li key={`${nextKey("li")}-${itemIndex}`}>{renderInline(item, nextKey("li-inline"))}</li>)}</Tag>);
      continue;
    }

    const paragraph: string[] = [];
    while (index < lines.length) {
      const candidate = lines[index].trim();
      if (
        !candidate ||
        candidate.startsWith(">") ||
        candidate.startsWith("```") ||
        HEADING_PATTERN.test(candidate) ||
        UL_PATTERN.test(candidate) ||
        OL_PATTERN.test(candidate) ||
        HR_PATTERN.test(candidate) ||
        isTableStart(lines, index)
      ) break;
      paragraph.push(candidate);
      index += 1;
    }
    if (!paragraph.length) { index += 1; continue; }
    nodes.push(
      <p key={nextKey("paragraph")}>
        {paragraph.map((line, lineIndex) => (
          <React.Fragment key={`${nextKey("line")}-${lineIndex}`}>
            {lineIndex > 0 ? <br /> : null}
            {renderInline(line, nextKey("line-inline"))}
          </React.Fragment>
        ))}
      </p>,
    );
  }
  return nodes;
}

/** Render Markdown as plain React elements. */
export function Markdown({ text, className, hideAnswers = false }: MarkdownProps) {
  const nodes = renderLines(String(text || "").split(/\r?\n/), hideAnswers, "md");
  if (!nodes.length) return null;
  return <div className={className ?? "md-body"}>{nodes}</div>;
}

export default Markdown;
