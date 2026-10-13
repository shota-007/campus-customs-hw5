import { useState } from "react";
import { API_URL } from "../api";
import { Avatar } from "../agents";
import { islandDate } from "../format";

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}

interface Props {
  dateToday?: string;
  online: boolean | null;
  approver: string;
  onApprover: (name: string) => void;
  onReset: () => void;
  resetDisabled: boolean;
}

export function Header({ dateToday, online, approver, onApprover, onReset, resetDisabled }: Props) {
  const [editing, setEditing] = useState(!approver);
  const [draft, setDraft] = useState(approver);

  const save = () => {
    const name = draft.trim();
    if (name) {
      onApprover(name);
      setEditing(false);
    }
  };

  return (
    <header className="topbar glass">
      <div className="brand">
        <svg viewBox="0 0 64 64" className="brand-mark" aria-hidden="true">
          <circle cx="32" cy="32" r="30" fill="#e9f6fd" />
          <circle cx="44" cy="21" r="9" fill="#ffc861" />
          <path d="M8 42c6-5 10-5 16 0s10 5 16 0 10-5 16 0v12H8z" fill="#1673b8" />
          <path d="M8 48c6-4 10-4 16 0s10 4 16 0 10-4 16 0" stroke="#fff" strokeWidth="3" fill="none" />
        </svg>
        <div>
          <div className="brand-name">Campus Customs <span>Shoreline Desk</span></div>
          <div className="brand-tag">Your agent crew, on island time.</div>
        </div>
      </div>

      <div className="topbar-mid">
        <span className="chip chip-date" title="desk.date_today: the shop's 'today'">
          🌴 Island date <b>{islandDate(dateToday)}</b>
        </span>
        <span className={`chip chip-conn ${online ? "ok" : online === false ? "down" : ""}`} title={API_URL}>
          <i /> {online ? "Backend connected" : online === false ? "Backend offline" : "Connecting…"}
        </span>
      </div>

      <div className="topbar-right">
        <div className="me">
          <Avatar agent="you" size={34} ring={false} />
          {editing ? (
            <form
              className="me-form"
              onSubmit={(e) => {
                e.preventDefault();
                save();
              }}
            >
              <input
                autoFocus
                value={draft}
                placeholder="Your name (for approvals)"
                onChange={(e) => setDraft(e.target.value)}
                aria-label="Your name, recorded as the approver"
              />
              <button className="btn btn-small" type="submit" disabled={!draft.trim()}>Sit down</button>
            </form>
          ) : (
            <button className="me-name" onClick={() => setEditing(true)} title="Change who is at the desk">
              <span>{greeting()},</span> <b>{approver}</b> ✎
            </button>
          )}
        </div>
        <button className="btn btn-ghost" onClick={onReset} disabled={resetDisabled} title="Copy the original shop database back">
          🌅 New day
        </button>
      </div>
    </header>
  );
}
