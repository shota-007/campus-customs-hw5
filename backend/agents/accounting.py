"""Accounting: cash, invoices, margins, and payment / PO requests for human approval."""

from ..models import AccountingReport
from .spec import RoleSpec

ACCOUNTING = RoleSpec(
    role="accounting",
    title="Accounting",
    prompt_file="accounting.md",
    output_type=AccountingReport,
    mcp_tools=frozenset({
        "get_ticket", "get_cash_position", "check_vendor_status", "quote_bulk_price",
        "list_payment_requests", "request_payment", "log_ticket_note",
    }),
)
