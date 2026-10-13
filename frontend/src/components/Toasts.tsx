export interface Toast {
  id: number;
  tone: "ok" | "warm" | "error" | "info";
  text: string;
}

export function Toasts({ toasts, onDismiss }: { toasts: Toast[]; onDismiss: (id: number) => void }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((t) => (
        <button key={t.id} className={`toast toast-${t.tone}`} onClick={() => onDismiss(t.id)}>
          {t.text}
        </button>
      ))}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirm,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  body: string;
  confirm: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal glass" role="dialog" aria-modal="true" aria-labelledby="modal-title" onClick={(e) => e.stopPropagation()}>
        <h2 id="modal-title">{title}</h2>
        <p>{body}</p>
        <div className="modal-actions">
          <button className="btn btn-ghost" onClick={onCancel}>Not yet</button>
          <button className="btn btn-surf" onClick={onConfirm} autoFocus>{confirm}</button>
        </div>
      </div>
    </div>
  );
}
