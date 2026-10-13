import { useEffect, useRef, useState } from "react";
import { money } from "../format";
import type { Cash, PaymentRequest } from "../types";

/** Tween a number so balance changes are felt, not just seen. */
function useAnimatedNumber(target: number | undefined, ms = 1400): number | undefined {
  const [value, setValue] = useState(target);
  const from = useRef(target);
  useEffect(() => {
    if (target == null) return;
    const start = from.current ?? target;
    if (start === target) {
      setValue(target);
      return;
    }
    const t0 = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / ms);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(start + (target - start) * eased);
      if (p < 1) raf = requestAnimationFrame(step);
      else from.current = target;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, ms]);
  return value;
}

export function CashTide({ cash, paid }: { cash: Cash | null; paid: PaymentRequest[] }) {
  const balance = useAnimatedNumber(cash?.balance);
  const [drop, setDrop] = useState<{ amount: number; key: number } | null>(null);
  const last = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (cash == null) return;
    if (last.current != null && cash.balance < last.current) {
      setDrop({ amount: last.current - cash.balance, key: Date.now() });
      const t = window.setTimeout(() => setDrop(null), 4500);
      last.current = cash.balance;
      return () => window.clearTimeout(t);
    }
    last.current = cash.balance;
  }, [cash]);

  // The pool's "full" mark is today's opening balance: what's left plus what has been paid out.
  const paidTotal = paid.reduce((s, p) => s + p.amount, 0);
  const opening = (cash?.balance ?? 0) + paidTotal;
  const level = opening > 0 && cash ? cash.balance / opening : 0;
  const afterPending = opening > 0 && cash ? Math.max(0, cash.available_to_commit) / opening : 0;

  return (
    <section className="card glass cash" aria-labelledby="cash-title">
      <div className="card-kicker" id="cash-title">The Tide · {cash?.account ?? "checking"}</div>
      <div className="cash-figure">
        <span className="cash-amount">{money(balance)}</span>
        {drop && (
          <span key={drop.key} className="cash-drop">−{money(drop.amount)}</span>
        )}
      </div>
      <div className="cash-sub">Cash on hand · as of {cash?.as_of ?? "—"} · only flows out</div>

      <div className="tidepool" role="img" aria-label={`Checking is at ${Math.round(level * 100)}% of today's opening balance`}>
        <div className="water" style={{ height: `${Math.max(4, level * 100)}%` }}>
          <svg viewBox="0 0 200 20" preserveAspectRatio="none" className="water-crest">
            <path d="M0 10 C 25 0, 50 20, 75 10 C 100 0, 125 20, 150 10 C 175 0, 200 20, 225 10 V20 H0 Z" />
          </svg>
        </div>
        {cash && cash.pending_total > 0 && (
          <div className="pending-line" style={{ bottom: `${afterPending * 100}%` }}>
            <span>if all approved: {money(cash.available_to_commit)}</span>
          </div>
        )}
        <div className="pool-mark">opening {money(opening)}</div>
      </div>

      <dl className="cash-stats">
        <div>
          <dt>Waiting on your OK</dt>
          <dd className={cash && cash.pending_total > 0 ? "warm" : ""}>{money(cash?.pending_total)}</dd>
        </div>
        <div>
          <dt>Free to commit</dt>
          <dd>{money(cash?.available_to_commit)}</dd>
        </div>
      </dl>

      {paid.length > 0 && (
        <ul className="paid-list">
          {paid.map((p) => (
            <li key={p.id}>
              <span>✓ {money(p.amount)} → {p.payee}</span>
              <small>approved by {p.decided_by}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
