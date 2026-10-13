import { useState } from "react";
import { AGENTS, Avatar } from "../agents";
import { KIND_LABEL, money } from "../format";
import type { PaymentRequest } from "../types";

interface Props {
  pending: PaymentRequest[];
  decided: PaymentRequest[];
  balance: number | undefined;
  approver: string;
  busyId: number | null;
  onApprove: (req: PaymentRequest) => void;
  onReject: (req: PaymentRequest, reason: string) => void;
  onFocusTicket: (id: number) => void;
}

export function ApprovalInbox({ pending, decided, balance, approver, busyId, onApprove, onReject, onFocusTicket }: Props) {
  const [declining, setDeclining] = useState<number | null>(null);
  const [reason, setReason] = useState("");

  return (
    <section className={`card glass inbox ${pending.length ? "has-pending" : ""}`} aria-labelledby="inbox-title">
      <div className="card-head">
        <div className="card-kicker" id="inbox-title">Needs your OK</div>
        {pending.length > 0 ? <span className="live-pill warm"><i /> {pending.length} waiting</span> : <span className="count-pill">all clear</span>}
      </div>
      <p className="inbox-rule">Agents can only <em>prepare</em> a payment. Nothing leaves checking until you approve it here.</p>

      {pending.length === 0 && (
        <div className="inbox-empty">
          <span aria-hidden="true">🐚</span> Nothing to sign. Kick back.
        </div>
      )}

      <ul className="requests">
        {pending.map((r) => {
          const kind = KIND_LABEL[r.kind] ?? { icon: "💸", label: r.kind };
          const tooMuch = balance != null && r.amount > balance;
          return (
            <li key={r.id} className="request">
              <div className="request-top">
                <span className="request-kind">{kind.icon} {kind.label}</span>
                <span className="request-amount">{money(r.amount)}</span>
              </div>
              <div className="request-payee">to <b>{r.payee}</b></div>
              <p className="request-reason">{r.reason}</p>
              <div className="request-meta">
                <Avatar agent={r.requested_by} size={22} ring={false} />
                <span>prepared by {AGENTS[r.requested_by]?.name ?? r.requested_by}</span>
                {r.ticket_id != null && (
                  <button className="link" onClick={() => onFocusTicket(r.ticket_id!)}>ticket #{r.ticket_id}</button>
                )}
                <span className="muted">req #{r.id}</span>
              </div>
              {tooMuch && <div className="request-warn">More than checking holds. The pay tool will refuse it.</div>}

              {declining === r.id ? (
                <form
                  className="decline-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (reason.trim()) {
                      onReject(r, reason.trim());
                      setDeclining(null);
                      setReason("");
                    }
                  }}
                >
                  <input autoFocus value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why decline?" />
                  <button className="btn btn-small" type="submit" disabled={!reason.trim()}>Decline</button>
                  <button className="btn btn-small btn-ghost" type="button" onClick={() => setDeclining(null)}>Cancel</button>
                </form>
              ) : (
                <div className="request-actions">
                  <button
                    className="btn btn-approve"
                    onClick={() => onApprove(r)}
                    disabled={!approver || busyId === r.id}
                    title={approver ? `Recorded as approved_by = ${approver}` : "Enter your name at the top first"}
                  >
                    {busyId === r.id ? <span className="spinner" /> : "✓"} Approve &amp; pay
                  </button>
                  <button className="btn btn-ghost" onClick={() => setDeclining(r.id)} disabled={busyId === r.id}>
                    Decline
                  </button>
                </div>
              )}
              {!approver && <small className="muted">Add your name at the top so the approval is signed.</small>}
            </li>
          );
        })}
      </ul>

      {decided.length > 0 && (
        <details className="decided">
          <summary>Decided ({decided.length})</summary>
          <ul>
            {decided.map((r) => (
              <li key={r.id} className={`decided-${r.status}`}>
                <span>{r.status === "paid" ? "✓ Paid" : r.status === "refused" ? "⛔ Refused" : "✗ Declined"}</span>{" "}
                {money(r.amount)} → {r.payee}
                <small> · {r.decided_by}{r.decision_note ? `: ${r.decision_note}` : ""}</small>
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
