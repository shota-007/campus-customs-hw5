"""Boss: reads each ticket, decides who works on it, and makes the final call."""

from ..models import BossDecision
from .spec import RoleSpec

BOSS = RoleSpec(
    role="boss",
    title="Boss (operations lead)",
    prompt_file="boss.md",
    output_type=BossDecision,
    mcp_tools=frozenset({
        "list_open_tickets", "get_ticket", "get_cash_position", "list_payment_requests",
        "log_ticket_note", "set_ticket_status",
    }),
)
