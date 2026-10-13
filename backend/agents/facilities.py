"""Facilities: the shop space side: leases, rent, landlord notices."""

from ..models import FacilitiesReport
from .spec import RoleSpec

FACILITIES = RoleSpec(
    role="facilities",
    title="Facilities",
    prompt_file="facilities.md",
    output_type=FacilitiesReport,
    mcp_tools=frozenset({"get_ticket", "get_lease", "get_cash_position", "log_ticket_note"}),
)
