import { useEffect, useRef } from "react";
import { AGENTS, Avatar, agentColor, agentName, agentTint, isRole } from "../agents";
import { clock, pretty, toolCall, toolWords } from "../format";
import type { FeedEvent } from "../types";

function ToolChips({ e }: { e: FeedEvent }) {
  return (
    <div className="tool-chips">
      {e.tools.map((t, i) => (
        <details key={i} className="tool-chip">
          <summary>
            <span className="tool-icon">🔧</span> {toolWords(t.tool)}
            <code>{t.tool}</code>
          </summary>
          <pre>{toolCall(t.tool, t.args)}</pre>
        </details>
      ))}
    </div>
  );
}

function ToolResults({ e }: { e: FeedEvent }) {
  return (
    <div className="tool-results">
      {e.tool_results.map((r, i) => (
        <details key={i} className={`tool-result ${r.error ? "refused" : ""}`}>
          <summary>
            {r.error ? "⛔ Refused by the shop rules" : "↩︎ Result"} · <code>{r.tool}</code>
          </summary>
          <pre>{pretty(r.content)}</pre>
        </details>
      ))}
    </div>
  );
}

function Line({ e }: { e: FeedEvent }) {
  const color = agentColor(e.agent);
  const indent = Math.min(e.depth, 3);
  const human = !isRole(e.agent);

  if (e.event === "delegation") {
    const to = String((e.tools[0]?.args as { to_agent?: string })?.to_agent ?? "");
    const refused = e.said?.includes("[refused:");
    return (
      <li className={`radio-line handoff depth-${indent}`}>
        <div className="handoff-card" style={{ borderColor: `${color}55` }}>
          <div className="handoff-route">
            <Avatar agent={e.agent} size={26} ring={false} />
            <span className="relay">⇢ {refused ? "tried to hand off to" : "hands off to"} ⇢</span>
            <Avatar agent={to} size={26} ring={false} />
            <b style={{ color: agentColor(to) }}>{agentName(to)}</b>
            <time>{clock(e.ts)}</time>
          </div>
          <p className="handoff-task">{e.said?.replace(/^→ \w+: /, "")}</p>
        </div>
      </li>
    );
  }

  if (e.event === "model_request") {
    return (
      <li className={`radio-line results depth-${indent}`}>
        <ToolResults e={e} />
      </li>
    );
  }

  const kind =
    e.event === "run_start" ? "start" :
    e.event === "final_answer" ? "final" :
    e.event === "run_end" ? "end" :
    e.event === "error" ? "error" :
    human ? "human" : "talk";

  if (kind === "end") {
    return (
      <li className={`radio-line end depth-${indent}`}>
        <span className="end-mark" style={{ color }}>✓ {agentName(e.agent)} wrapped up</span>
      </li>
    );
  }

  return (
    <li className={`radio-line ${kind} depth-${indent}`}>
      <Avatar agent={e.agent} size={34} />
      <div className="bubble" style={{ background: agentTint(e.agent), borderColor: `${color}40` }}>
        <div className="bubble-head">
          <b style={{ color }}>{agentName(e.agent)}</b>
          {isRole(e.agent) && <span className="creature">{AGENTS[e.agent].creature}</span>}
          {kind === "start" && <span className="tag">picks up the task</span>}
          {kind === "final" && <span className="tag tag-final">report</span>}
          {kind === "error" && <span className="tag tag-error">stopped</span>}
          {kind === "human" && <span className="tag tag-human">{e.event.replace("payment_", "payment ")}</span>}
          <time>{clock(e.ts)}</time>
        </div>
        {e.said && (
          kind === "start" ? (
            <details className="task">
              <summary>{e.said.slice(0, 150)}{e.said.length > 150 ? "…" : ""}</summary>
              <p>{e.said}</p>
            </details>
          ) : (
            <p className="said">{e.said}</p>
          )
        )}
        {e.tools.length > 0 && <ToolChips e={e} />}
      </div>
    </li>
  );
}

interface Props {
  feed: FeedEvent[];
  live: boolean;
  liveLine: string | null;
  emptyHint: string;
}

export function CrewRadio({ feed, live, liveLine, emptyHint }: Props) {
  const box = useRef<HTMLOListElement>(null);
  const stick = useRef(true);

  useEffect(() => {
    const el = box.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [feed.length, live]);

  return (
    <section className="card glass radio" aria-labelledby="radio-title">
      <div className="card-head">
        <div className="card-kicker" id="radio-title">Crew radio</div>
        {live ? <span className="live-pill"><i /> live</span> : <span className="count-pill">{feed.length} messages</span>}
      </div>
      <ol
        className="radio-feed"
        ref={box}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
        aria-live="polite"
      >
        {feed.length === 0 && <li className="radio-empty">{emptyHint}</li>}
        {feed.map((e) => <Line key={e.seq} e={e} />)}
        {live && liveLine && (
          <li className="radio-line typing">
            <span className="typing-dots" aria-hidden="true"><i /><i /><i /></span>
            <span>{liveLine}</span>
          </li>
        )}
      </ol>
    </section>
  );
}
