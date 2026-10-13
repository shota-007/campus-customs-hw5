// All dashboard state in one place: polls the backend, fast while the crew works, slow when idle.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import { ROLES } from "./agents";
import type {
  AgentOutput,
  BossDecision,
  Cash,
  FeedEvent,
  PaymentRequest,
  Role,
  RunInfo,
  TicketDetail,
  TicketsResponse,
} from "./types";

const FAST_MS = 1500;
const SLOW_MS = 5000;
const HUMAN_EVENTS = new Set(["payment_approved", "payment_refused", "payment_rejected"]);

export interface RunSummary {
  runId: string;
  ticketId: number;
  startSeq: number;
  startTs: string;
  lastTs: string;
  beforeReset: boolean;
  finished: boolean;
}

export interface AgentActivity {
  role: Role;
  status: "idle" | "working" | "done" | "stopped";
  outputs: AgentOutput[];
  tools: string[];
  handoffs: string[];
  last: FeedEvent | null;
}

export function useDesk(selectedTicket: number | null) {
  const [board, setBoard] = useState<TicketsResponse | null>(null);
  const [cash, setCash] = useState<Cash | null>(null);
  const [pending, setPending] = useState<PaymentRequest[]>([]);
  const [decided, setDecided] = useState<PaymentRequest[]>([]);
  const [events, setEvents] = useState<FeedEvent[]>([]);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const [finishedRun, setFinishedRun] = useState<RunInfo | null>(null);

  const lastSeq = useRef(-1);
  const prevActive = useRef<string | null>(null);
  const selectedRef = useRef(selectedTicket);
  selectedRef.current = selectedTicket;

  const refresh = useCallback(async () => {
    try {
      const [t, c, p, all, ev] = await Promise.all([
        api.tickets(),
        api.cash(),
        api.payments("pending"),
        api.payments("all"),
        api.events(lastSeq.current),
      ]);
      setBoard(t);
      setCash(c);
      setPending(p.requests);
      setDecided(all.requests.filter((r) => r.status !== "pending").reverse());
      if (ev.last_seq < lastSeq.current) {
        // audit trail was replaced; reload from scratch next tick
        lastSeq.current = -1;
        setEvents([]);
      } else if (ev.events.length) {
        const maxSeq = ev.events[ev.events.length - 1].seq;
        lastSeq.current = ev.events.length >= 1000 ? maxSeq : Math.max(maxSeq, ev.last_seq);
        // Merge by seq: overlapping polls (e.g. React StrictMode in dev) must never duplicate an event.
        setEvents((prev) => {
          const bySeq = new Map(prev.map((e) => [e.seq, e]));
          for (const e of ev.events) bySeq.set(e.seq, e);
          return [...bySeq.values()].sort((a, b) => a.seq - b.seq).slice(-4000);
        });
      } else {
        lastSeq.current = Math.max(lastSeq.current, ev.last_seq);
      }

      const active = t.active_run?.run_id ?? null;
      if (prevActive.current && !active) {
        const done = await api.run(prevActive.current).catch(() => null);
        if (done) setFinishedRun(done);
      }
      prevActive.current = active;

      if (selectedRef.current != null) {
        setDetail(await api.ticket(selectedRef.current));
      }
      setOnline(true);
    } catch {
      setOnline(false);
    }
  }, []);

  const activeRun = board?.active_run ?? null;

  useEffect(() => {
    let alive = true;
    let timer: number | undefined;
    const loop = async () => {
      await refresh();
      if (alive) timer = window.setTimeout(loop, prevActive.current ? FAST_MS : SLOW_MS);
    };
    loop();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [refresh]);

  // Load the selected ticket's detail right away when the selection changes.
  useEffect(() => {
    setDetail(null);
    if (selectedTicket != null) api.ticket(selectedTicket).then(setDetail).catch(() => undefined);
  }, [selectedTicket]);

  const lastResetSeq = useMemo(
    () => events.reduce((m, e) => (e.event === "db_reset" ? Math.max(m, e.seq) : m), -1),
    [events],
  );

  const runsByTicket = useMemo(() => {
    const map = new Map<number, RunSummary[]>();
    const byRun = new Map<string, RunSummary>();
    for (const e of events) {
      if (e.ticket_id == null || !/^t\d+-/.test(e.run_id)) continue;
      let r = byRun.get(e.run_id);
      if (!r) {
        r = {
          runId: e.run_id,
          ticketId: e.ticket_id,
          startSeq: e.seq,
          startTs: e.ts,
          lastTs: e.ts,
          beforeReset: e.seq < lastResetSeq,
          finished: false,
        };
        byRun.set(e.run_id, r);
        map.set(e.ticket_id, [...(map.get(e.ticket_id) ?? []), r]);
      }
      r.lastTs = e.ts;
      if (e.agent === "boss" && e.depth === 0 && (e.event === "run_end" || e.event === "error")) r.finished = true;
    }
    return map;
  }, [events, lastResetSeq]);

  return { board, cash, pending, decided, events, detail, online, activeRun, refresh, runsByTicket, lastResetSeq, finishedRun, setFinishedRun };
}

/** Events to show for one run: the run itself plus human decisions on that ticket afterwards. */
export function runFeed(events: FeedEvent[], run: RunSummary | null): FeedEvent[] {
  if (!run) return [];
  return events.filter(
    (e) =>
      e.run_id === run.runId ||
      (HUMAN_EVENTS.has(e.event) && e.ticket_id === run.ticketId && e.seq > run.startSeq),
  );
}

export function crewActivity(feed: FeedEvent[], runActive: boolean): AgentActivity[] {
  return ROLES.map((role) => {
    const mine = feed.filter((e) => e.agent === role);
    const starts = mine.filter((e) => e.event === "run_start").length;
    const ends = mine.filter((e) => e.event === "run_end").length;
    const errored = mine.some((e) => e.event === "error");
    const status: AgentActivity["status"] = !mine.length
      ? "idle"
      : starts > ends
        ? runActive && !errored
          ? "working"
          : "stopped"
        : "done";
    return {
      role,
      status,
      outputs: mine.filter((e) => e.event === "run_end" && e.output).map((e) => e.output as AgentOutput),
      tools: [...new Set(mine.flatMap((e) => e.tools.map((t) => t.tool)).filter((t) => t !== "delegate"))],
      handoffs: mine.filter((e) => e.event === "delegation").map((e) => String((e.tools[0]?.args as { to_agent?: string })?.to_agent ?? "")),
      last: mine[mine.length - 1] ?? null,
    };
  });
}

export function bossDecision(feed: FeedEvent[]): BossDecision | null {
  const end = [...feed].reverse().find((e) => e.agent === "boss" && e.depth === 0 && e.event === "run_end");
  return (end?.output as BossDecision | undefined) ?? null;
}
