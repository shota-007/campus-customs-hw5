import { AGENTS, Avatar, agentName } from "../agents";
import { toolWords } from "../format";
import type { AgentActivity } from "../useDesk";

const STATUS_TEXT = { idle: "on the beach", working: "working", done: "done", stopped: "stopped" } as const;

function nowDoing(a: AgentActivity): string | null {
  const e = a.last;
  if (!e || a.status !== "working") return null;
  if (e.event === "delegation") return "waiting on a teammate";
  if (e.tools.length) return toolWords(e.tools[e.tools.length - 1].tool).toLowerCase() + "…";
  if (e.event === "run_start") return "reading the task…";
  return "thinking…";
}

export function CrewRoster({ crew, hasRun, live }: { crew: AgentActivity[]; hasRun: boolean; live: boolean }) {
  return (
    <section className="card glass roster" aria-labelledby="roster-title">
      <div className="card-head">
        <div className="card-kicker" id="roster-title">The crew on this ticket</div>
      </div>
      <ul className="crew">
        {crew.map((a) => {
          const meta = AGENTS[a.role];
          const doing = nowDoing(a);
          return (
            <li key={a.role} className={`crew-card status-${a.status}`} style={{ ["--agent" as string]: meta.color, ["--agent-tint" as string]: meta.tint }}>
              <div className="crew-head">
                <div className={`crew-avatar ${a.status === "working" ? "bob" : ""}`}>
                  <Avatar agent={a.role} size={42} />
                </div>
                <div className="crew-id">
                  <b>{meta.name}</b>
                  <small>{meta.creature}</small>
                </div>
                <span className={`crew-status s-${a.status}`}>{STATUS_TEXT[a.status]}</span>
              </div>

              {doing && <div className="crew-doing">{doing}</div>}

              {a.outputs.length > 0 ? (
                <div className="crew-summary">
                  {a.outputs.map((o, i) => <p key={i}>{o.summary}</p>)}
                  {a.outputs.some((o) => o.actions_taken?.length) && (
                    <ul className="crew-actions">
                      {a.outputs.flatMap((o) => o.actions_taken ?? []).slice(0, 4).map((x, i) => <li key={i}>{x}</li>)}
                    </ul>
                  )}
                </div>
              ) : a.status === "idle" ? (
                <p className="crew-blurb">{live ? "Standing by in case the crew calls." : hasRun ? "Not needed on this ticket." : meta.blurb}</p>
              ) : null}

              {(a.tools.length > 0 || a.handoffs.length > 0) && (
                <div className="crew-tools">
                  {a.tools.map((t) => <code key={t}>{t}</code>)}
                  {a.handoffs.filter(Boolean).map((h, i) => <code key={`h${i}`} className="handoff-code">→ {agentName(h)}</code>)}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
