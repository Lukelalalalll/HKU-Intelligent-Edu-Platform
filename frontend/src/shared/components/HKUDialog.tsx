import React, { useEffect, useId, useRef } from "react";

export type HKUDialogScope = "viewport" | "surface";

export type HKUDialogProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: React.ReactNode;
  eyebrow?: string;
  icon?: React.ReactNode;
  scope?: HKUDialogScope;
  children?: React.ReactNode;
  className?: string;
  labelledBy?: string;
};

/** Shared HKU dialog shell. Keep the backdrop inside a positioned surface when it should not cover app chrome. */
export function HKUDialog({ open, onClose, title, description, eyebrow, icon, scope = "viewport", children, className = "", labelledBy }: HKUDialogProps) {
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const onCloseRef = useRef(onClose);
  const generatedTitleId = useId();
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onCloseRef.current(); };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  if (!open) return null;
  const titleId = labelledBy || `hku-dialog-title-${generatedTitleId}`;
  return (
    <div className={`hku-dialog-backdrop hku-dialog-${scope}`} role="presentation" onMouseDown={onClose}>
      <section className={`hku-dialog ${className}`} role="dialog" aria-modal="true" aria-labelledby={titleId} onMouseDown={(event) => event.stopPropagation()}>
        <button ref={closeRef} className="hku-dialog-close" type="button" onClick={onClose} aria-label="关闭">×</button>
        {icon ? <div className="hku-dialog-icon" aria-hidden="true">{icon}</div> : null}
        {eyebrow ? <span className="ppt-kicker">{eyebrow}</span> : null}
        <h2 id={titleId}>{title}</h2>
        {description ? <p>{description}</p> : null}
        {children}
      </section>
    </div>
  );
}

export type HKUConfirmDialogProps = Omit<HKUDialogProps, "children"> & {
  onConfirm: () => void | Promise<void>;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
  confirmTone?: "danger" | "primary";
};

export function HKUConfirmDialog({ onConfirm, confirmLabel = "确认", cancelLabel = "取消", loading = false, confirmTone = "danger", onClose, ...dialogProps }: HKUConfirmDialogProps) {
  return (
    <HKUDialog {...dialogProps} onClose={onClose}>
      <div className="hku-dialog-actions">
        <button type="button" className="ppt-ghost" onClick={onClose} disabled={loading}>{cancelLabel}</button>
        <button type="button" className={`hku-dialog-confirm ${confirmTone === "danger" ? "is-danger" : ""}`} onClick={() => void onConfirm()} disabled={loading}>{loading ? "处理中…" : confirmLabel}</button>
      </div>
    </HKUDialog>
  );
}
