"""Customer Service: drafts customer messages. Drafts stay on the board; nothing is sent."""

from ..models import CustomerServiceReport
from .spec import RoleSpec

CUSTOMER_SERVICE = RoleSpec(
    role="customer_service",
    title="Customer Service",
    prompt_file="customer_service.md",
    output_type=CustomerServiceReport,
    mcp_tools=frozenset({"get_ticket", "check_stock", "quote_bulk_price", "save_customer_draft", "log_ticket_note"}),
)
