"""Campus Customs backend: FastAPI routes the React dashboard calls.

Start it from the backend/ folder:
    uvicorn main:app --reload --port 8000
(or from the project root: uvicorn backend.main:app --reload --port 8000)

Every shop read and write goes through the Campus Customs MCP server, the same
door the agents use. The dashboard holds one MCP connection for human actions
(listing, approving), and the agent team holds its own.
Agents only *request* payments. POST /payments/{id}/approve is the only route
that moves cash, and it needs the name of the human who clicked Approve.
"""

import asyncio
import os
import sys
import uuid
from contextlib import AsyncExitStack, asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:  # lets `uvicorn main:app` run from inside backend/
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from fastapi import FastAPI, HTTPException, Query  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from backend import audit  # noqa: E402
from backend.mcp_link import human_mcp_client  # noqa: E402
from backend.reset_db import reset_working_db  # noqa: E402
from backend.team import CampusCustomsTeam  # noqa: E402

# --------------------------------------------------------------------------
# App lifetime: one MCP connection for humans, one agent team (with its own)
# --------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        app.state.human = await stack.enter_async_context(human_mcp_client())
        try:
            app.state.team = await stack.enter_async_context(CampusCustomsTeam())
            app.state.team_error = None
        except Exception as exc:  # e.g. missing PORTKEY_API_KEY: dashboard still works, runs don't
            app.state.team, app.state.team_error = None, f"{type(exc).__name__}: {exc}"
        app.state.runs: dict[str, dict] = {}
        app.state.active_run: str | None = None
        app.state.tasks: set[asyncio.Task] = set()
        yield
        for task in app.state.tasks:
            task.cancel()


app = FastAPI(
    title="Campus Customs Multi-Agent Operations",
    version="1.0",
    description="Ticket board, agent runs, audit feed, human payment approval, cash, and reset.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    # The Vite dashboard (http://localhost:5173 by default; Vite moves to 5174+ if that port is busy).
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)


async def mcp_call(tool: str, **args: Any) -> Any:
    """Call a shop tool over MCP as the human/dashboard. Tool refusals become HTTP errors."""
    try:
        result = await app.state.human.call_tool(tool, args)
    except ToolError as exc:
        message = str(exc)
        raise HTTPException(status_code=404 if message.startswith("No ") else 400, detail=message) from exc
    return result.data if result.data is not None else result.structured_content


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------


class ApproveBody(BaseModel):
    approved_by: str = Field(min_length=1, description="Name of the human who clicked Approve.")


class RejectBody(BaseModel):
    rejected_by: str = Field(min_length=1)
    reason: str = Field(min_length=1)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


@app.get("/")
async def index() -> dict:
    return {
        "service": "Campus Customs backend",
        "agents_ready": app.state.team is not None,
        "agents_error": app.state.team_error,
        "active_run": app.state.active_run,
        "routes": [f"{', '.join(sorted(r.methods - {'HEAD'}))} {r.path}" for r in app.routes if hasattr(r, "methods")],
    }


# ---- 1. Tickets -------------------------------------------------------------


@app.get("/tickets")
async def list_tickets() -> dict:
    """All tickets with status and whether each is open or resolved."""
    data = await mcp_call("list_tickets")
    data["active_run"] = app.state.active_run and app.state.runs.get(app.state.active_run)
    return data


@app.get("/tickets/{ticket_id}")
async def ticket_detail(ticket_id: int) -> dict:
    """One ticket with its linked lease/invoice and all work done on it (holds, POs, payment requests, drafts, log)."""
    return await mcp_call("get_ticket", ticket_id=ticket_id)


# ---- 2. Run the agent team on a ticket ----------------------------------------


async def _execute_run(run_id: str, ticket_id: int) -> None:
    run = app.state.runs[run_id]
    try:
        result = await app.state.team.run_ticket(ticket_id, run_id=run_id)
        if hasattr(result, "model_dump"):
            run.update(status="done", result=result.model_dump(mode="json"))
        else:
            run.update(status=f"stopped_{result.get('stopped', 'error')}", result=result)
    except asyncio.CancelledError:
        run.update(status="cancelled")
        raise
    except Exception as exc:
        run.update(status="stopped_error", result={"reason": f"{type(exc).__name__}: {exc}"})
    finally:
        run["finished_at"] = _now()
        if app.state.active_run == run_id:
            app.state.active_run = None


@app.post("/tickets/{ticket_id}/run")
async def run_ticket(ticket_id: int, wait: bool = Query(False, description="Block until the run finishes.")):
    """Start the agent team on one ticket. Returns 202 + run_id; poll /runs/{run_id} and /events."""
    if app.state.team is None:
        raise HTTPException(503, f"Agent team unavailable: {app.state.team_error}")
    await mcp_call("get_ticket", ticket_id=ticket_id)  # 404 if the ticket doesn't exist
    if app.state.active_run:  # one run at a time: tickets compete for the same cash
        raise HTTPException(409, f"Run {app.state.active_run} is still in progress.")

    run_id = f"t{ticket_id}-{uuid.uuid4().hex[:8]}"
    app.state.active_run = run_id
    app.state.runs[run_id] = {
        "run_id": run_id, "ticket_id": ticket_id, "status": "running",
        "started_at": _now(), "finished_at": None, "result": None,
    }
    task = asyncio.create_task(_execute_run(run_id, ticket_id))
    app.state.tasks.add(task)
    task.add_done_callback(app.state.tasks.discard)

    if wait:
        await asyncio.shield(task)
        return app.state.runs[run_id]
    return JSONResponse(status_code=202, content=app.state.runs[run_id])


@app.get("/runs")
async def list_runs() -> dict:
    return {"active_run": app.state.active_run, "runs": list(app.state.runs.values())[::-1]}


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = app.state.runs.get(run_id)
    if run is None:
        raise HTTPException(404, f"No run {run_id} since the server started.")
    return run


# ---- 3. Recent agent events (from output/audit_trail.json) ----------------------


def _feed_item(seq: int, e: dict) -> dict | None:
    """Condense one audit event into 'who said what, which tools they used'."""
    detail, kind = e.get("detail", {}), e["event"]
    item = {
        "seq": seq, "ts": e["ts"], "run_id": e["run_id"], "agent_run_id": e.get("agent_run_id"), "ticket_id": e["ticket_id"],
        "agent": e["agent"], "chain": e.get("chain", []), "depth": e.get("depth", 0),
        "event": kind, "said": None, "tools": [], "tool_results": [],
        "tokens_so_far": e.get("usage", {}).get("total_tokens"), "model": e.get("model"),
    }
    if kind == "model_response":
        parts = detail.get("parts", [])
        calls = [p for p in parts if p["type"] == "tool_call"]
        texts = [p["content"] for p in parts if p["type"] == "text" and p.get("content")]
        final = next((c for c in calls if c["tool"] == "final_result"), None)
        item["tools"] = [{"tool": c["tool"], "args": c["args"]} for c in calls if c["tool"] != "final_result"]
        if texts:
            item["said"] = "\n".join(texts)
        elif final and isinstance(final["args"], dict):
            item["said"] = final["args"].get("summary") or final["args"].get("decision")
            item["event"] = "final_answer"
    elif kind == "model_request":
        results = [p for p in detail.get("parts", []) if p["type"] in ("tool_return", "tool_error_or_retry")]
        if not results:
            return None
        item["tool_results"] = [
            {"tool": p.get("tool"), "error": p["type"] == "tool_error_or_retry", "content": p.get("content")}
            for p in results
        ]
    elif kind == "delegation":
        item["said"] = f"→ {detail.get('to')}: {detail.get('task')}"
        item["tools"] = [{"tool": "delegate", "args": {"to_agent": detail.get("to"), "task": detail.get("task")}}]
        if detail.get("refused"):
            item["said"] += f"  [refused: {detail['refused']}]"
    elif kind == "run_start":
        item["said"] = detail.get("prompt")
    elif kind == "run_end":
        output = detail.get("output") or {}
        item["said"] = output.get("summary") if isinstance(output, dict) else output
        item["output"] = output
    elif kind == "error":
        item["said"] = f"{detail.get('type')}: {detail.get('message')}"
    elif kind in ("payment_approved", "payment_refused", "payment_rejected", "db_reset"):
        item["said"] = detail.get("summary")
        item["output"] = detail
    else:  # user_prompt duplicates run_start
        return None
    return item


@app.get("/events")
async def events(
    after: int = Query(-1, description="Only events with seq greater than this (for incremental refresh)."),
    limit: int = Query(100, ge=1, le=1000),
    ticket_id: int | None = None,
    run_id: str | None = None,
    raw: bool = Query(False, description="Return full audit events instead of the condensed feed."),
) -> dict:
    """Recent agent events: what each agent said and which tools it used. Oldest first."""
    all_events = audit.read_events()
    picked = []
    for seq, e in enumerate(all_events):
        if seq <= after or (ticket_id is not None and e["ticket_id"] != ticket_id) or (run_id and e["run_id"] != run_id):
            continue
        item = {"seq": seq, **e} if raw else _feed_item(seq, e)
        if item is not None:
            picked.append(item)
    picked = picked[:limit] if after >= 0 else picked[-limit:]
    return {"last_seq": len(all_events) - 1, "count": len(picked), "events": picked}


# ---- 4. Human approval: the only route that moves cash ---------------------------


@app.get("/payments")
async def payments(status: Literal["pending", "paid", "rejected", "refused", "all"] = "pending") -> dict:
    """Payment and purchase-order requests the agents prepared (default: waiting for a human)."""
    return await mcp_call("list_payment_requests", status=status)


@app.post("/payments/{request_id}/approve")
async def approve_payment(request_id: int, body: ApproveBody) -> dict:
    """Human clicked Approve: pay the invoice / rent / purchase order from checking.

    The MCP pay tool re-checks cash and refuses (status 'refused') rather than go negative.
    On success it writes `payments` (approved_by), lowers `cash_accounts.balance`, and updates
    the invoice, lease next_due, or purchase order.
    """
    result = await mcp_call("approve_payment", request_id=request_id, approved_by=body.approved_by)
    paid = result["status"] == "paid"
    summary = (
        f"{body.approved_by} approved request #{request_id}: paid ${result['amount']:,.2f} to {result['payee']}; "
        f"checking ${result['balance_before']:,.2f} → ${result['balance_after']:,.2f}"
        if paid else f"Pay tool refused request #{request_id}: {result['reason']}"
    )
    audit.record_human("payment_approved" if paid else "payment_refused", ticket_id=result.get("ticket_id"),
                       actor=body.approved_by, detail={"summary": summary, **result})
    return result


@app.post("/payments/{request_id}/reject")
async def reject_payment(request_id: int, body: RejectBody) -> dict:
    result = await mcp_call("reject_payment", request_id=request_id, rejected_by=body.rejected_by, reason=body.reason)
    audit.record_human("payment_rejected", ticket_id=result.get("ticket_id"), actor=body.rejected_by,
                       detail={"summary": f"{body.rejected_by} rejected request #{request_id}: {body.reason}", **result})
    return result


# ---- 5. Cash ----------------------------------------------------------------------


@app.get("/cash")
async def cash() -> dict:
    """Current checking balance from cash_accounts, plus what is pending against it."""
    data = await mcp_call("get_cash_position")
    return {
        "account": data["account"],
        "balance": data["balance"],
        "as_of": data["balance_as_of"],
        "pending_total": data["pending_total"],
        "available_to_commit": data["available_to_commit"],
        "pending_requests": data["pending_requests"],
        "date_today": data["date_today"],
    }


# ---- 6. Reset --------------------------------------------------------------------


@app.post("/reset")
async def reset() -> dict:
    """Copy the untouched original over the working DB for a fresh run. The audit trail is kept."""
    if app.state.active_run:
        raise HTTPException(409, f"Run {app.state.active_run} is in progress; reset after it finishes.")
    reset_working_db()
    tickets = await mcp_call("list_tickets")
    cash_now = await mcp_call("get_cash_position")
    summary = f"Working DB reset from the original: {tickets['count']} tickets, checking ${cash_now['balance']:,.2f}"
    audit.record_human("db_reset", actor="system", detail={"summary": summary})
    return {"ok": True, "summary": summary, "tickets": tickets["tickets"], "balance": cash_now["balance"]}
