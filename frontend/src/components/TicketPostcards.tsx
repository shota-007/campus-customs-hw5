import { TYPE_LABEL, boardStatus } from "../format";
import type { RunInfo, Ticket } from "../types";

interface Props {
  tickets: Ticket[];
  selected: number | null;
  activeRun: RunInfo | null;
  onSelect: (id: number) => void;
}

export function TicketPostcards({ tickets, selected, activeRun, onSelect }: Props) {
  const open = tickets.filter((t) => t.state === "open").length;
  return (
    <section className="card glass tickets" aria-labelledby="tickets-title">
      <div className="card-head">
        <div className="card-kicker" id="tickets-title">Ticket board</div>
        <span className="count-pill">{open} open · {tickets.length - open} resolved</span>
      </div>
      <div className="postcards">
        {tickets.map((t, i) => {
          const type = TYPE_LABEL[t.type] ?? { icon: "📌", label: t.type };
          const running = activeRun?.ticket_id === t.id;
          const resolved = t.state === "resolved";
          return (
            <button
              key={t.id}
              className={`postcard ${selected === t.id ? "selected" : ""} ${resolved ? "is-resolved" : ""} ${running ? "is-running" : ""}`}
              onClick={() => onSelect(t.id)}
              style={{ ["--tilt" as string]: `${[-0.6, 0.5, -0.3][i % 3]}deg` }}
              aria-pressed={selected === t.id}
            >
              <div className="stamp" aria-hidden="true"><span>{type.icon}</span></div>
              <div className="postcard-top">
                <span className="ticket-no">#{t.id}</span>
                <span className="ticket-type">{type.label}</span>
              </div>
              <div className="postcard-subject">{t.subject}</div>
              <div className="postcard-from">from {t.requester}</div>
              {t.sku && (
                <div className="postcard-line">{t.qty} × {t.sku}{t.size ? ` · size ${t.size}` : ""}</div>
              )}
              <div className="postcard-foot">
                {running ? (
                  <span className="state running"><i className="wave-dot" />Crew on it…</span>
                ) : resolved ? (
                  <span className={`state resolved status-${t.status}`}>Resolved · {boardStatus(t)}</span>
                ) : (
                  <span className="state open">Open · waiting for the crew</span>
                )}
                <span className="badges">
                  {t.pending_payment_requests > 0 && <span className="badge warm" title="Payment requests waiting for your OK">💸 {t.pending_payment_requests}</span>}
                  {t.customer_drafts > 0 && <span className="badge" title="Customer drafts (not sent)">✉️ {t.customer_drafts}</span>}
                </span>
              </div>
              {resolved && <div className="ink-stamp" aria-hidden="true">RESOLVED</div>}
            </button>
          );
        })}
      </div>
    </section>
  );
}
