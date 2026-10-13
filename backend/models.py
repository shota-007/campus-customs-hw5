"""Data types for the Campus Customs agent team.

Each agent returns a typed report, so the agent that delegated the work (and
the dashboard later) gets structured facts instead of free text. Every report
carries `facts`: each number or claim names the MCP tool it came from, which
makes it easy to audit that nothing was invented.
"""

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

Role = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
ROLES: tuple[Role, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")
TicketStatus = Literal["open", "in_progress", "waiting_approval", "waiting_customer", "blocked", "resolved"]


# --------------------------------------------------------------------------
# Shared pieces
# --------------------------------------------------------------------------


class Fact(BaseModel):
    """One fact the agent relied on, tied to the tool that returned it."""

    source_tool: str = Field(description="MCP tool that returned this fact, e.g. 'check_stock'.")
    detail: str = Field(description="The fact in plain words with the exact value, e.g. 'CC-HOOD-NAVY M qty_on_hand = 8'.")


class AgentReport(BaseModel):
    """Fields every agent returns."""

    ticket_id: int
    summary: str = Field(description="Two or three sentences: what you found and what you did.")
    facts: list[Fact] = Field(default_factory=list, description="Every number you used, with its source tool.")
    actions_taken: list[str] = Field(default_factory=list, description="Database changes you made (ids included). Empty if none.")
    needs_human: list[str] = Field(default_factory=list, description="Decisions only a human can make (payment approvals, discounts over policy).")
    blockers: list[str] = Field(default_factory=list, description="What stops this ticket from moving forward right now.")


# --------------------------------------------------------------------------
# Specialist reports
# --------------------------------------------------------------------------


class InventoryReport(AgentReport):
    sku: str | None = None
    size: str | None = None
    qty_requested: int | None = None
    qty_on_hand: int | None = None
    shortfall: int | None = None
    hold_ids: list[int] = Field(default_factory=list, description="stock_holds ids created for this ticket.")
    restock_vendor: str | None = Field(default=None, description="Vendor name from check_vendor_status, if a restock is needed.")
    vendor_can_ship: bool | None = None
    blocking_invoice_ids: list[int] = Field(default_factory=list)
    po_id: int | None = Field(default=None, description="Draft purchase order id, if one was drafted.")
    earliest_arrival: str | None = Field(default=None, description="ISO date from the tools, only if the vendor can ship.")
    recommendation: str


class AccountingReport(AgentReport):
    cash_balance: float | None = None
    pending_total: float | None = None
    available_to_commit: float | None = None
    payment_request_ids: list[int] = Field(default_factory=list, description="Payment requests created and now waiting for a human.")
    refused: list[str] = Field(default_factory=list, description="Payment requests the tools refused, with the tool's reason.")
    discount_pct_recommended: float | None = None
    margin_check: str | None = Field(default=None, description="Result of quote_bulk_price, if a discount was checked.")
    recommendation: str


class FacilitiesReport(AgentReport):
    lease_id: int | None = None
    space_name: str | None = None
    landlord: str | None = None
    monthly_rent: float | None = None
    next_due: str | None = None
    days_until_due: int | None = None
    payment_request_id: int | None = None
    recommendation: str


class CustomerServiceReport(AgentReport):
    draft_ids: list[int] = Field(default_factory=list, description="customer_drafts ids saved (never sent).")
    recipient: str | None = None
    promises_made: list[str] = Field(default_factory=list, description="Every commitment in the draft (price, quantity, date), each backed by a fact.")


# --------------------------------------------------------------------------
# Boss outputs
# --------------------------------------------------------------------------


class TriageItem(BaseModel):
    ticket_id: int
    priority: int = Field(description="1 = handle first.")
    owners: list[Role] = Field(description="Agents the Boss expects to involve.")
    why: str


class TriagePlan(BaseModel):
    """Boss's ordering of the open board before working any ticket."""

    items: list[TriageItem]
    cash_note: str = Field(description="How cash constrains the order of work.")


class BossDecision(AgentReport):
    final_status: TicketStatus
    decision: str = Field(description="The Boss's final call on this ticket and why.")
    agents_consulted: list[Role] = Field(default_factory=list)
    payment_requests_awaiting_human: list[int] = Field(default_factory=list)
    customer_draft_ids: list[int] = Field(default_factory=list)
    follow_ups: list[str] = Field(default_factory=list, description="What must happen next, and who does it.")


ROLE_OUTPUT: dict[Role, type[AgentReport]] = {
    "boss": BossDecision,
    "inventory": InventoryReport,
    "accounting": AccountingReport,
    "facilities": FacilitiesReport,
    "customer_service": CustomerServiceReport,
}


# --------------------------------------------------------------------------
# Run-time state passed to every agent (PydanticAI deps)
# --------------------------------------------------------------------------


@dataclass
class TicketBudget:
    """Shared by every agent working one ticket, so hand-offs are counted once for the whole ticket."""

    delegations_used: int = 0


@dataclass
class TeamDeps:
    run_id: str                    # one id per ticket run, shared by all nested agents
    ticket_id: int | None
    agent: Role                    # the agent this deps object belongs to
    chain: tuple[Role, ...]        # who delegated to whom to get here, e.g. ("boss", "inventory")
    depth: int = 0
    budget: TicketBudget = field(default_factory=TicketBudget)
    agent_run_id: str = ""         # id of this single agent loop (for the audit trail)

    def for_delegate(self, role: Role) -> "TeamDeps":
        return TeamDeps(
            run_id=self.run_id,
            ticket_id=self.ticket_id,
            agent=role,
            chain=(*self.chain, role),
            depth=self.depth + 1,
            budget=self.budget,
        )


# --------------------------------------------------------------------------
# Audit trail record
# --------------------------------------------------------------------------


class AuditEvent(BaseModel):
    ts: str
    run_id: str
    agent_run_id: str
    ticket_id: int | None
    agent: str = Field(description="An agent role, or 'human' / 'system' for dashboard actions.")
    chain: list[str]
    depth: int
    step: int
    event: str = Field(description="run_start | user_prompt | model_request | model_response | delegation | run_end | error | payment_approved | payment_rejected | db_reset")
    model: str | None = None
    detail: dict = Field(default_factory=dict)
    usage: dict = Field(default_factory=dict, description="Cumulative tokens/requests for the whole ticket at this step.")
