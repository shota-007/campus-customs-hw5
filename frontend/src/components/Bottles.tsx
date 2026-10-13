import { AGENTS } from "../agents";
import type { CustomerDraft, TicketDetail } from "../types";

function Bottle() {
  return (
    <svg viewBox="0 0 40 64" className="bottle" aria-hidden="true">
      <rect x="15" y="2" width="10" height="7" rx="2" fill="#b07a45" />
      <path d="M14 9 h12 v8 q8 6 8 16 v22 q0 7 -7 7 h-14 q-7 0 -7 -7 v-22 q0 -10 8 -16 z" fill="#bfe7f5" stroke="#7cc4ef" strokeWidth="2" />
      <rect x="11" y="30" width="18" height="14" rx="2" fill="#fff7e6" transform="rotate(-8 20 37)" />
      <path d="M14 35 h11 M14 39 h8" stroke="#d6b98a" strokeWidth="1.4" transform="rotate(-8 20 37)" />
    </svg>
  );
}

export function Bottles({ detail }: { detail: TicketDetail | null }) {
  const drafts: CustomerDraft[] = detail?.work_so_far.customer_drafts ?? [];
  const holds = detail?.work_so_far.stock_holds ?? [];
  const pos = detail?.work_so_far.purchase_orders ?? [];

  return (
    <section className="card glass bottles" aria-labelledby="bottles-title">
      <div className="card-head">
        <div className="card-kicker" id="bottles-title">Messages in a bottle</div>
        <span className="count-pill">drafts · never sent</span>
      </div>
      {drafts.length === 0 ? (
        <p className="muted small">No customer drafts on this ticket yet. Customer Service writes them; you send them.</p>
      ) : (
        drafts.map((d) => (
          <article key={d.id} className="draft">
            <div className="draft-head">
              <Bottle />
              <div>
                <div className="draft-to">To {d.recipient}</div>
                <div className="draft-subject">{d.subject}</div>
                <small className="muted">draft #{d.id} by {AGENTS[d.author as keyof typeof AGENTS]?.name ?? d.author} · not sent</small>
              </div>
            </div>
            <p className="draft-body">{d.body}</p>
          </article>
        ))
      )}

      {(holds.length > 0 || pos.length > 0) && (
        <div className="work-strip">
          {holds.map((h) => (
            <span key={`h${String(h.id)}`} className="fact-chip">
              📌 Hold #{String(h.id)}: {String(h.qty)} × {String(h.sku)} {String(h.size)} ({String(h.status)})
            </span>
          ))}
          {pos.map((p) => (
            <span key={`p${String(p.id)}`} className="fact-chip">
              📦 PO #{String(p.id)}: {String(p.qty)} × {String(p.sku)} {String(p.size)} · ${String(p.total)} ({String(p.status)})
            </span>
          ))}
        </div>
      )}
    </section>
  );
}
