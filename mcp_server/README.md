# Campus Customs MCP Server

**What it's for:** this server is the one shared toolbox for the Campus Customs agent team (Boss, Inventory, Accounting, Facilities, Customer Service). It's the only way the agents reach shop data; there is no second tools layer. The tools return only what's in the shop database, and they raise an error instead of guessing when a record doesn't exist. The shop rules are enforced here in code, not just in prompts:
- human approval for payments;
- no negative cash;
- no shipping from a vendor with an unpaid invoice;
- drafts only, never sent.

**Database:** `data/campus_customs_new.db`, the working copy. The original `data/campus_customs.db` is never opened, so it stays clean for resets (`python -m backend.reset_db`). You can override the path with the `CAMPUS_CUSTOMS_DB` environment variable.

The server creates its work tables in the working copy whenever they're missing (on start and after a reset): `payment_requests`, `purchase_orders`, `stock_holds`, `customer_drafts`, and `ticket_log`.

Built with [FastMCP](https://gofastmcp.com).

## Tools

### Read
| Tool | Reads | Returns |
|---|---|---|
| `list_open_tickets()` | `tickets`, `desk` | Every unresolved ticket, plus `date_today` |
| `list_tickets()` | `tickets`, `desk`, `payment_requests`, `customer_drafts` | Every ticket, open or resolved, with `state` and pending-request/draft counts (dashboard) |
| `get_ticket(ticket_id)` | `tickets`, `desk`, `leases`, `invoices`, `vendors`, work tables | The ticket, its linked lease or invoice with days due/overdue, and all work done on it so far |
| `check_stock(sku, size?, qty_needed?)` | `inventory`, `pricing` | Sizes on hand, cost, list price, margin, `can_fill_now`, `shortfall` |
| `check_vendor_status(vendor_id?)` | `vendors`, `invoices`, `desk` | Lead days, open invoices, `can_ship`, earliest arrival if ordered today |
| `get_lease(lease_id)` | `leases`, `desk`, `payment_requests` | Rent, landlord, `next_due`, days until due, existing rent requests |
| `get_cash_position()` | `cash_accounts`, `payment_requests`, `invoices`, `leases` | Balance, pending requests, `available_to_commit`, open invoices, rent due |
| `quote_bulk_price(sku, qty, discount_pct)` | `pricing` | Discounted price, total, margin %. Refuses prices below cost and flags discounts over 15% |
| `list_payment_requests(status)` | `payment_requests` | Requests by status |

### Write (agents; no money moves)
| Tool | Writes |
|---|---|
| `log_ticket_note(ticket_id, agent, note)` | `ticket_log` |
| `set_ticket_status(ticket_id, status, agent, reason)` | `tickets.status`, `ticket_log` |
| `hold_stock(ticket_id, sku, size, qty, agent)` | `inventory.qty` (−), `stock_holds` |
| `release_stock_hold(hold_id, agent, reason)` | `inventory.qty` (+), `stock_holds` |
| `draft_purchase_order(ticket_id, vendor_id, sku, size, qty, agent)` | `purchase_orders` (draft, costed from `pricing`) |
| `request_payment(kind, ref_id, ticket_id, reason, agent)` | `payment_requests` (pending). The amount is read from the invoice, lease, or PO. Refuses duplicates, blocked vendors, and anything above `available_to_commit` |
| `save_customer_draft(ticket_id, recipient, subject, body, agent)` | `customer_drafts`. Never sent |

### Human only (the backend never gives these to an agent)
| Tool | Writes |
|---|---|
| `approve_payment(request_id, approved_by)` | Re-checks cash and refuses if the balance would go negative. Otherwise: a `payments` row with `approved_by`, the `cash_accounts.balance` deduction, and then `invoices.status='paid'`, or `leases.next_due` moved +1 month, or `purchase_orders.status='ordered'` |
| `reject_payment(request_id, rejected_by, reason)` | `payment_requests` → rejected |

## Run

```bash
pip install -r requirements.txt
python -m mcp_server.server
```

The server speaks MCP over stdio. Run it from the project root. Claude Code picks it up from `.mcp.json`. The FastAPI backend (`backend/main.py`) starts two copies through `backend/mcp_link.py`: one for the agent team and one for human/dashboard actions.
