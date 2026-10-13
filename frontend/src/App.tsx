import { useCallback, useEffect, useMemo, useState } from "react";
import { API_URL, api } from "./api";
import { agentName } from "./agents";
import { STATUS_LABEL, money, toolWords } from "./format";
import type { BossDecision, PaymentRequest } from "./types";
import { bossDecision, crewActivity, runFeed, useDesk } from "./useDesk";
import { ApprovalInbox } from "./components/ApprovalInbox";
import { Bottles } from "./components/Bottles";
import { CashTide } from "./components/CashTide";
import { CrewRadio } from "./components/CrewRadio";
import { CrewRoster } from "./components/CrewRoster";
import { Header } from "./components/Header";
import { Scenery } from "./components/Scenery";
import { TicketPostcards } from "./components/TicketPostcards";
import { TicketStage } from "./components/TicketStage";
import { ConfirmDialog, Toasts, type Toast } from "./components/Toasts";

function useStoredString(key: string): [string, (v: string) => void] {
  const [value, setValue] = useState(() => localStorage.getItem(key) ?? "");
  const set = useCallback((v: string) => {
    localStorage.setItem(key, v);
    setValue(v);
  }, [key]);
  return [value, set];
}

export default function App() {
  const [selected, setSelected] = useState<number | null>(null);
  const desk = useDesk(selected);
  const [approver, setApprover] = useStoredString("shoreline-desk.approver");
  const [runChoice, setRunChoice] = useState<Record<number, string>>({});
  const [starting, setStarting] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirmReset, setConfirmReset] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((tone: Toast["tone"], text: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, tone, text }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6500);
  }, []);

  const tickets = desk.board?.tickets ?? [];

  // Pick the first open ticket once the board loads.
  useEffect(() => {
    if (selected == null && tickets.length) setSelected((tickets.find((t) => t.state === "open") ?? tickets[0]).id);
  }, [tickets, selected]);

  // Announce when a run finishes; the ticket flips to Resolved on the board.
  useEffect(() => {
    const done = desk.finishedRun;
    if (!done) return;
    if (done.status === "done" && done.result && "final_status" in done.result) {
      const d = done.result as BossDecision;
      toast("ok", `🏝️ Ticket #${done.ticket_id} resolved · ${STATUS_LABEL[d.final_status]}`);
    } else {
      const reason = (done.result as { reason?: string } | null)?.reason ?? done.status;
      toast("error", `Run on #${done.ticket_id} stopped: ${reason}`);
    }
    desk.setFinishedRun(null);
  }, [desk.finishedRun, desk, toast]);

  const ticket = tickets.find((t) => t.id === selected) ?? null;
  const runs = (selected != null && desk.runsByTicket.get(selected)) || [];
  const activeHere = desk.activeRun?.ticket_id === selected ? desk.activeRun.run_id : null;
  const wanted = (selected != null && runChoice[selected]) || activeHere;
  const run = runs.find((r) => r.runId === wanted) ?? [...runs].reverse().find((r) => !r.beforeReset) ?? null;
  const runActive = !!desk.activeRun && (run?.runId === desk.activeRun.run_id || (!run && !!activeHere));

  const feed = useMemo(() => runFeed(desk.events, run), [desk.events, run]);
  const crew = useMemo(() => crewActivity(feed, runActive), [feed, runActive]);
  const decision = useMemo(() => bossDecision(feed), [feed]);
  const tokens = useMemo(() => feed.reduce((m, e) => Math.max(m, e.tokens_so_far ?? 0), 0) || null, [feed]);

  const liveLine = useMemo(() => {
    if (!runActive) return null;
    const working = crew.filter((a) => a.status === "working" && a.last);
    if (!working.length) return "The crew is paddling out…";
    const a = working.reduce((x, y) => ((x.last?.seq ?? 0) > (y.last?.seq ?? 0) ? x : y));
    const e = a.last!;
    const doing =
      e.event === "delegation" ? "handing off" :
      e.tools.length ? toolWords(e.tools[e.tools.length - 1].tool).toLowerCase() :
      e.event === "model_request" ? "reading the results" : "thinking";
    return `${agentName(a.role)} is ${doing}…`;
  }, [crew, runActive]);

  const emptyHint = activeHere || starting
    ? "The crew is paddling out…"
    : runs.length
      ? "No crew run on this ticket since the last reset. Pick an older run above, or send the crew."
      : "Quiet waters. Send the crew and their radio chatter shows up here.";

  const sendCrew = async () => {
    if (!ticket) return;
    setStarting(true);
    try {
      const info = await api.runTicket(ticket.id);
      setRunChoice((c) => ({ ...c, [ticket.id]: info.run_id }));
      toast("info", `🏄 Crew paddled out to ticket #${ticket.id}`);
      await desk.refresh();
    } catch (err) {
      toast("error", `Couldn't start the crew: ${(err as Error).message}`);
    } finally {
      setStarting(false);
    }
  };

  const approve = async (req: PaymentRequest) => {
    setBusyId(req.id);
    try {
      const res = await api.approve(req.id, approver);
      if (res.status === "paid") {
        toast("ok", `✓ Paid ${money(res.amount)} to ${res.payee}. Checking ${money(res.balance_before)} → ${money(res.balance_after)}`);
      } else {
        toast("warm", `⛔ The pay tool refused #${req.id}: ${res.reason}`);
      }
      await desk.refresh();
    } catch (err) {
      toast("error", `Approval failed: ${(err as Error).message}`);
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (req: PaymentRequest, reason: string) => {
    setBusyId(req.id);
    try {
      await api.reject(req.id, approver || "desk", reason);
      toast("info", `Declined request #${req.id}. No money moved.`);
      await desk.refresh();
    } catch (err) {
      toast("error", `Decline failed: ${(err as Error).message}`);
    } finally {
      setBusyId(null);
    }
  };

  const reset = async () => {
    setConfirmReset(false);
    try {
      const res = await api.reset();
      setRunChoice({});
      toast("info", `🌅 New day. ${res.summary}`);
      await desk.refresh();
    } catch (err) {
      toast("error", `Reset failed: ${(err as Error).message}`);
    }
  };

  return (
    <>
      <Scenery />
      <div className="desk">
        <Header
          dateToday={desk.board?.date_today}
          online={desk.online}
          approver={approver}
          onApprover={setApprover}
          onReset={() => setConfirmReset(true)}
          resetDisabled={!!desk.activeRun || desk.online === false}
        />

        {desk.online === false && (
          <div className="offline glass">
            🌊 Can't reach the backend at <code>{API_URL}</code>. Start it from <code>backend/</code> with{" "}
            <code>uvicorn main:app --reload --port 8000</code>. This page retries on its own.
          </div>
        )}

        <main className="grid">
          <aside className="col col-left">
            <CashTide cash={desk.cash} paid={desk.decided.filter((r) => r.status === "paid")} />
            <TicketPostcards tickets={tickets} selected={selected} activeRun={desk.activeRun} onSelect={setSelected} />
          </aside>

          <section className="col col-center">
            {ticket ? (
              <TicketStage
                ticket={ticket}
                detail={desk.detail}
                runs={runs}
                run={run}
                onPickRun={(id) => selected != null && setRunChoice((c) => ({ ...c, [selected]: id }))}
                activeRun={desk.activeRun}
                starting={starting}
                onSend={sendCrew}
                decision={decision}
                tokens={tokens}
              />
            ) : (
              <section className="card glass stage stage-empty">Pick a ticket from the board to get started.</section>
            )}
            <CrewRadio feed={feed} live={runActive || (!!activeHere && !run)} liveLine={liveLine ?? (activeHere ? "The crew is paddling out…" : null)} emptyHint={emptyHint} />
          </section>

          <aside className="col col-right">
            <ApprovalInbox
              pending={desk.pending}
              decided={desk.decided}
              balance={desk.cash?.balance}
              approver={approver}
              busyId={busyId}
              onApprove={approve}
              onReject={reject}
              onFocusTicket={setSelected}
            />
            <CrewRoster crew={crew} hasRun={!!run} live={runActive} />
            <Bottles detail={desk.detail} />
          </aside>
        </main>

        <footer className="foot">
          Campus Customs · Shoreline Desk · five agents on <b>gpt-6-luna</b> · every step in <code>output/audit_trail.json</code> ·
          drafts never leave the board · cash only moves when you approve
        </footer>
      </div>

      <Toasts toasts={toasts} onDismiss={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />
      <ConfirmDialog
        open={confirmReset}
        title="Start a new day?"
        body="This copies the original shop database back over the working copy: all tickets reopen, cash returns to the opening balance, and requests, holds, and drafts are cleared. The audit trail is kept."
        confirm="🌅 Reset the shop"
        onConfirm={reset}
        onCancel={() => setConfirmReset(false)}
      />
    </>
  );
}
