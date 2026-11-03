/**
 * Minimal Markdown renderer for agent replies.
 *
 * Assistant messages are written as light Markdown. Rendering happens through
 * React nodes (never `dangerouslySetInnerHTML`), so model output cannot inject
 * markup. Supported: paragraphs, bullet/numbered lists, headings, bold,
 * italic and inline code.
 */
import React from "react";

const INLINE_PATTERN = /(\*\*[^*]+\*\*|\*[^*\n]+\*|`[^`\n]+`)/g;

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

type ListBlock = { ordered: boolean; items: string[] };

export type MarkdownProps = { text?: string | null; className?: string };

/** Render agent Markdown as plain React elements. */
export function Markdown({ text, className }: MarkdownProps) {
  const blocks: React.ReactNode[] = [];
  const lines = String(text || "").split(/\r?\n/);
  let list: ListBlock | null = null;
  let index = 0;

  const flushList = () => {
    if (!list) return;
    const current: ListBlock = list;
    list = null;
    const Tag = current.ordered ? "ol" : "ul";
    const listKey = `list-${blocks.length}`;
    blocks.push(
      <Tag key={listKey}>
        {current.items.map((item, itemIndex) => (
          <li key={`${listKey}-${itemIndex}`}>{renderInline(item, `${listKey}-${itemIndex}`)}</li>
        ))}
      </Tag>,
    );
  };

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) { flushList(); continue; }
    const bullet = /^[-*•]\s+(.*)$/.exec(trimmed);
    const ordered = /^\d+[.)]\s+(.*)$/.exec(trimmed);
    if (bullet || ordered) {
      const isOrdered = Boolean(ordered);
      if (!list || (list as ListBlock).ordered !== isOrdered) { flushList(); list = { ordered: isOrdered, items: [] }; }
      (list as ListBlock).items.push((bullet || ordered)?.[1] || "");
      continue;
    }
    flushList();
    const heading = /^#{1,4}\s+(.*)$/.exec(trimmed);
    if (heading) {
      blocks.push(<h4 key={`heading-${index++}`}>{renderInline(heading[1], `heading-${index}`)}</h4>);
      continue;
    }
    blocks.push(<p key={`paragraph-${index++}`}>{renderInline(trimmed, `paragraph-${index}`)}</p>);
  }
  flushList();

  if (!blocks.length) return null;
  return <div className={className ?? "md-body"}>{blocks}</div>;
}

export default Markdown;
