/**
 * Markdown editor dialog for one lesson plan page.
 */
import React, { useEffect, useState } from "react";
import type { LessonPlanPage } from "../../api";
import { useI18n } from "../../i18n";
import { HKUDialog } from "../../shared/components/HKUDialog";

export type LessonPlanEditorProps = {
  page: LessonPlanPage | null;
  saving: boolean;
  onSave: (markdown: string) => void;
  onClose: () => void;
};

/** Edit the Markdown source that both the preview and the exports render. */
export default function LessonPlanEditor({ page, saving, onSave, onClose }: LessonPlanEditorProps) {
  const { t } = useI18n();
  const [value, setValue] = useState("");

  useEffect(() => {
    setValue(page?.markdown || "");
  }, [page?.id, page?.revision]);

  const dirty = Boolean(page) && value.trim() !== (page?.markdown || "").trim();
  const canSave = Boolean(value.trim()) && dirty && !saving;

  return (
    <HKUDialog
      open={Boolean(page)}
      onClose={onClose}
      title={t("lessonPlan.editor.title")}
      description={t("lessonPlan.editor.hint")}
      eyebrow="EDIT PAGE"
      className="lesson-editor-dialog"
    >
      <textarea
        className="lesson-editor-textarea"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={18}
        spellCheck={false}
        aria-label={t("lessonPlan.editor.title")}
      />
      <div className="lesson-editor-actions">
        <button type="button" className="lesson-button secondary" onClick={onClose} disabled={saving}>{t("lessonPlan.editor.cancel")}</button>
        <button type="button" className="lesson-button primary" onClick={() => onSave(value.trim())} disabled={!canSave}>
          {saving ? t("lessonPlan.editor.saving") : t("lessonPlan.editor.save")}
        </button>
      </div>
    </HKUDialog>
  );
}
