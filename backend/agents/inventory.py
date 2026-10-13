"""Inventory: stock by SKU and size, shortfalls, holds, and which vendor can restock."""

from ..models import InventoryReport
from .spec import RoleSpec

INVENTORY = RoleSpec(
    role="inventory",
    title="Inventory",
    prompt_file="inventory.md",
    output_type=InventoryReport,
    mcp_tools=frozenset({
        "get_ticket", "check_stock", "check_vendor_status", "hold_stock", "release_stock_hold",
        "draft_purchase_order", "log_ticket_note",
    }),
)
