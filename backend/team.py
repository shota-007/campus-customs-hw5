"""The Campus Customs agent team: five PydanticAI agents with full connectivity.

Every agent has the same `delegate` tool and may hand work to any other agent.
Brakes keep that from turning into an endless chat:
  * no delegating to yourself or to anyone already waiting in the current chain,
  * a depth cap and a per-ticket hand-off cap,
  * one shared usage counter per ticket, so UsageLimits caps requests, tool
    calls, and tokens for the Boss *and* everyone it pulls in.

Each agent loop is driven step by step with `agent.iter`, and every step
(prompt in, model response out, tool results, delegation, final output) is
appended to output/audit_trail.json.
"""

import uuid
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.usage import RunUsage, UsageLimits

from . import audit
from .agents import ROLE_SPECS, RoleSpec
from .config import (
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    MODEL_NAME,
    MODEL_SETTINGS,
    TICKET_LIMITS,
    TRIAGE_LIMITS,
    build_model,
)
from .mcp_link import build_mcp_toolset
from .models import ROLES, BossDecision, Role, TeamDeps, TicketBudget, TriagePlan


class ModelMismatchError(RuntimeError):
    """Raised if Portkey ever serves anything other than gpt-6-luna."""


def _roster(current: Role) -> str:
    lines = [f"- `{s.role}`: {s.title}" for s in ROLE_SPECS.values() if s.role != current]
    return "## Your teammates (reachable with `delegate`)\n" + "\n".join(lines)


def _run_context(ctx: RunContext[TeamDeps]) -> str:
    d = ctx.deps
    waiting = [r for r in d.chain if r != d.agent]
    left = MAX_DELEGATIONS_PER_TICKET - d.budget.delegations_used
    can_go_deeper = d.depth < MAX_DELEGATION_DEPTH
    return (
        "## Run context\n"
        f"- You are `{d.agent}`. Ticket: {f'#{d.ticket_id}' if d.ticket_id is not None else 'none (triage mode)'}.\n"
        f"- Delegation chain: {' -> '.join(d.chain)} (depth {d.depth} of max {MAX_DELEGATION_DEPTH}).\n"
        f"- Waiting on you right now (do NOT delegate to them): {', '.join(waiting) or 'nobody'}.\n"
        f"- Hand-offs left for this ticket: {left}."
        + ("" if can_go_deeper else " You are at max depth: you cannot delegate; answer with what you have.")
        + "\n- Facts come only from MCP tool results in this run or teammates' reports. Today = date_today from the tools."
    )


class CampusCustomsTeam:
    """Owns the model, the one MCP connection, and the five agents."""

    def __init__(self) -> None:
        self.model = build_model()
        self.mcp = build_mcp_toolset()
        self.agents: dict[Role, Agent] = {role: self._build_agent(spec) for role, spec in ROLE_SPECS.items()}

    async def __aenter__(self) -> "CampusCustomsTeam":
        await self.mcp.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.mcp.__aexit__(*exc)

    # ------------------------------------------------------------------ build

    def _build_agent(self, spec: RoleSpec) -> Agent:
        allowed = spec.mcp_tools
        agent: Agent[TeamDeps, Any] = Agent(
            self.model,
            name=spec.role,
            deps_type=TeamDeps,
            output_type=spec.output_type,
            instructions=spec.prompt + "\n\n" + _roster(spec.role),
            toolsets=[self.mcp.filtered(lambda ctx, tool_def: tool_def.name in allowed)],
            model_settings=MODEL_SETTINGS,
            retries=2,
        )
        agent.instructions(_run_context)

        team = self

        @agent.tool
        async def delegate(ctx: RunContext[TeamDeps], to_agent: Role, task: str) -> dict:
            """Hand part of this ticket to another agent and wait for its typed report.

            to_agent: one of boss, inventory, accounting, facilities, customer_service (not yourself,
            and not anyone already waiting in the delegation chain).
            task: a self-contained request: the ticket id, exactly what you need back, and the facts
            you already have (with numbers and their source tool) so they do not re-check them.
            """
            return await team._delegate(ctx, to_agent, task)

        return agent

    # ------------------------------------------------------------ delegation

    async def _delegate(self, ctx: RunContext[TeamDeps], to_agent: Role, task: str) -> dict:
        d = ctx.deps
        refusal = None
        if to_agent not in ROLES:
            refusal = f"Unknown agent {to_agent!r}. Choose one of {', '.join(ROLES)}."
        elif d.ticket_id is None:
            refusal = "Delegation is off in triage mode. Return your TriagePlan."
        elif to_agent == d.agent:
            refusal = "You cannot delegate to yourself."
        elif to_agent in d.chain:
            refusal = (f"{to_agent} is already waiting on you in this chain ({' -> '.join(d.chain)}). "
                       "Put your question or finding in your report instead.")
        elif d.depth >= MAX_DELEGATION_DEPTH:
            refusal = f"Max delegation depth ({MAX_DELEGATION_DEPTH}) reached. Answer with what you have."
        elif d.budget.delegations_used >= MAX_DELEGATIONS_PER_TICKET:
            refusal = f"This ticket used all {MAX_DELEGATIONS_PER_TICKET} hand-offs. Finish with what you have."

        audit.record(d, ctx.run_step, "delegation",
                     detail={"to": to_agent, "task": task, "refused": refusal}, usage=ctx.usage)
        if refusal:
            return {"delegated": False, "reason": refusal}

        d.budget.delegations_used += 1
        child = d.for_delegate(to_agent)
        try:
            report = await self.run_agent(to_agent, task, child, usage=ctx.usage)
        except UsageLimitExceeded:
            raise  # the ticket's token/request budget is a hard stop for everyone
        except Exception as exc:  # a teammate failing should not crash the caller's loop
            return {"delegated": True, "agent": to_agent, "error": f"{type(exc).__name__}: {exc}"}
        return {"delegated": True, "agent": to_agent, "report": report.model_dump(mode="json")}

    # ------------------------------------------------------------ agent loop

    async def run_agent(
        self,
        role: Role,
        prompt: str,
        deps: TeamDeps,
        *,
        usage: RunUsage | None = None,
        output_type: Any = None,
        limits: UsageLimits = TICKET_LIMITS,
    ) -> Any:
        """Run one agent loop step by step, auditing every node."""
        deps.agent_run_id = f"{role}-{uuid.uuid4().hex[:8]}"
        agent = self.agents[role]
        audit.record(deps, 0, "run_start", detail={"prompt": prompt}, usage=usage)
        step = 0
        try:
            async with agent.iter(
                prompt, deps=deps, usage=usage, usage_limits=limits,
                **({"output_type": output_type} if output_type else {}),
            ) as run:
                async for node in run:
                    step += 1
                    event, detail = audit.describe_node(node)
                    served = detail.get("served_model")
                    audit.record(deps, step, event, model=served, detail=detail, usage=run.usage)
                    if served and not served.startswith(MODEL_NAME):
                        raise ModelMismatchError(f"Portkey served {served!r}; only {MODEL_NAME} is allowed.")
                return run.result.output
        except Exception as exc:
            audit.record(deps, step + 1, "error", detail={"type": type(exc).__name__, "message": str(exc)}, usage=usage)
            raise

    # ------------------------------------------------------------ entry points

    async def triage(self) -> TriagePlan:
        """Boss looks at the whole board once and orders the work."""
        deps = TeamDeps(run_id=f"triage-{uuid.uuid4().hex[:8]}", ticket_id=None, agent="boss", chain=("boss",))
        return await self.run_agent(
            "boss",
            "Triage mode: order the open board. Call list_open_tickets and get_cash_position once each, "
            "do not delegate, and return a TriagePlan.",
            deps,
            output_type=TriagePlan,
            limits=TRIAGE_LIMITS,
        )

    async def _apply_final_status(self, ticket_id: int, decision: BossDecision) -> None:
        """Safety net: if the Boss returned a final call but forgot set_ticket_status, record it."""
        current = await self.mcp.direct_call_tool("get_ticket", {"ticket_id": ticket_id})
        if current["ticket"]["status"] != decision.final_status:
            await self.mcp.direct_call_tool("set_ticket_status", {
                "ticket_id": ticket_id, "status": decision.final_status, "agent": "boss",
                "reason": f"(applied from the Boss's final decision) {decision.decision}"[:500],
            })

    async def run_ticket(self, ticket_id: int, board_note: str = "", run_id: str | None = None) -> BossDecision | dict:
        """Boss works one ticket end to end, pulling in teammates as needed."""
        run_id = run_id or f"t{ticket_id}-{uuid.uuid4().hex[:8]}"
        deps = TeamDeps(run_id=run_id, ticket_id=ticket_id, agent="boss", chain=("boss",), budget=TicketBudget())
        prompt = (
            f"Work ticket #{ticket_id} end to end: read it, route it to the right specialists, "
            "make the final call, set its status, and return your BossDecision."
            + (f"\n\nBoard context from triage: {board_note}" if board_note else "")
        )
        usage = RunUsage()
        try:
            decision = await self.run_agent("boss", prompt, deps, usage=usage)
            await self._apply_final_status(ticket_id, decision)
            return decision
        except UsageLimitExceeded as exc:
            return {"ticket_id": ticket_id, "run_id": run_id, "stopped": "budget", "reason": str(exc)}
        except Exception as exc:
            return {"ticket_id": ticket_id, "run_id": run_id, "stopped": "error", "reason": f"{type(exc).__name__}: {exc}"}
