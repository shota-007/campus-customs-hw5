import { AGENTS, Avatar } from "../agents";
import { STATUS_LABEL, TYPE_LABEL, boardStatus, clock, duration } from "../format";
import type { RunSummary } from "../useDesk";
import type { BossDecision, RunInfo, Ticket, TicketDetail } from "../types";

interface Props {
  ticket: Ticket;
  detail: TicketDetail | null;
  runs: RunSummary[];
  run: RunSummary | null;
  onPickRun: (runId: string) => void;
  activeRun: RunInfo | null;
  starting: boolean;
  onSend: () => void;
  decision: BossDecision | null;
  tokens: number | null;
}

export function TicketStage({ ticket, detail, runs, run, onPickRun, activeRun, starting, onSend, decision, tokens }: Props) {
  const type = TYPE_LABEL[ticket.type] ?? { icon: "📌", label: ticket.type };
  const busyHere = activeRun?.ticket_id === ticket.id;
  const busyElsewhere = !!activeRun && !busyHere;
  const lease = detail?.lease as { monthly_rent?: number; next_due?: string; days_until_due?: number } | null;
  const invoice = detail?.invoice as { id?: number; amount?: number; days_overdue?: number; vendor_name?: string } | null;

  return (
    <section className="card glass stage" aria-labelledby="stage-title">
      <div className="stage-head">
        <div className="stage-icon" aria-hidden="true">{type.icon}</div>
        <div className="stage-title">
          <div className="card-kicker">#{ticket.id} · {type.label} · from {ticket.requester}</div>
          <h1 id="stage-title">{ticket.subject}</h1>
          <p className="stage-note">“{ticket.notes}”</p>
          <div className="stage-facts">
            {ticket.sku && <span className="fact-chip">{ticket.qty} × {ticket.sku}{ticket.size ? ` · ${ticket.size}` : ""}</span>}
            {lease?.monthly_rent != null && <span className="fact-chip">Lease rent ${lease.monthly_rent.toLocaleString()} · due {lease.next_due} ({lease.days_until_due}d)</span>}
            {invoice?.id != null && <span className="fact-chip warm">Invoice #{invoice.id} · ${invoice.amount} · {invoice.vendor_name}{invoice.days_overdue ? ` · ${invoice.days_overdue}d overdue` : ""}</span>}
            <span className={`fact-chip status status-${ticket.status}`}>{ticket.state === "resolved" ? "Resolved · " : ""}{boardStatus(ticket)}</span>
          </div>
        </div>
        <div className="stage-cta">
          <button className="btn btn-surf" onClick={onSend} disabled={!!activeRun || starting}>
            {busyHere || starting ? <><span className="spinner" /> Crew is out…</> : ticket.state === "resolved" ? "🏄 Send the crew again" : "🏄 Send the crew"}
          </button>
          {busyElsewhere && <small>Crew is on ticket #{activeRun?.ticket_id}. One ticket at a time (they share the cash).</small>}
          {runs.length > 0 && (
            <label className="run-pick">
              <span>Run</span>
              <select value={run?.runId ?? ""} onChange={(e) => onPickRun(e.target.value)}>
                {[...runs].reverse().map((r) => (
                  <option key={r.runId} value={r.runId}>
                    {clock(r.startTs)} · {r.runId}{r.beforeReset ? " (before reset)" : ""}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      </div>

      {decision && run && (
        <div className="captains-log">
          <div className="log-head">
            <Avatar agent="boss" size={38} />
            <div>
              <div className="card-kicker">Captain's log · the Boss's final call</div>
              <div className="log-status">
                <span className={`status-pill status-${decision.final_status}`}>{STATUS_LABEL[decision.final_status]}</span>
                <span className="muted">
                  {duration(run.startTs, run.lastTs)} · {tokens?.toLocaleString() ?? "—"} tokens ·{" "}
                  crew: {decision.agents_consulted.map((a) => AGENTS[a]?.name ?? a).join(", ") || "Boss only"}
                </span>
              </div>
            </div>
          </div>
          <p className="log-decision">{decision.decision}</p>
          <div className="log-grid">
            {decision.needs_human.length > 0 && (
              <div className="log-box warm">
                <h4>Needs you</h4>
                <ul>{decision.needs_human.map((n, i) => <li key={i}>{n}</li>)}</ul>
              </div>
            )}
            {decision.follow_ups.length > 0 && (
              <div className="log-box">
                <h4>Next up</h4>
                <ul>{decision.follow_ups.map((n, i) => <li key={i}>{n}</li>)}</ul>
              </div>
            )}
            {decision.blockers.length > 0 && (
              <div className="log-box blockers">
                <h4>Blockers</h4>
                <ul>{decision.blockers.map((n, i) => <li key={i}>{n}</li>)}</ul>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
