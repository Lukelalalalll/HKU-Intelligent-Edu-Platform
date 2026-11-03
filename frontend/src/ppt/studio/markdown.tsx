/**
 * Backwards-compatible re-export of the shared Markdown renderer.
 *
 * The renderer moved to ``shared/components`` so the lesson plan preview can
 * reuse it. Existing studio imports keep working through this module.
 */
export { Markdown, renderInline } from "../../shared/components/Markdown";
export type { MarkdownProps } from "../../shared/components/Markdown";
export { default } from "../../shared/components/Markdown";
