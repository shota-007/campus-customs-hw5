"""Campus Customs MCP server.

Every agent on the Campus Customs team (Boss, Inventory, Accounting,
Facilities, Customer Service) uses these tools. They read and write the
working copy data/campus_customs_new.db.

Ground rules enforced here, not just in prompts:
  * Tools only return what is in the database. Derived numbers (shortfall,
    days overdue, arrival date, margin) are plain arithmetic on database values.
    A missing record raises an error instead of a guess.
  * Money amounts are never typed by an agent. request_payment looks the amount
    up from the invoice, lease, or purchase order it pays.
  * Agents can only *request* a payment. Money moves in approve_payment, which
    requires a named human approver, re-checks cash, and refuses any payment
    that would push the balance below zero. The backend never gives the
    human-only tools to an agent.
  * Customer messages are saved as drafts on the board. Nothing is sent.

Run (stdio):  python -m mcp_server.server
"""

from datetime import date, timedelta
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

try:
    from .db import add_one_month, connect, ensure_schema, now_iso, row_to_dict, shop_today
except ImportError:  # run directly as a script: python mcp_server/server.py
    from db import add_one_month, connect, ensure_schema, now_iso, row_to_dict, shop_today

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES = {"boss", "inventory", "accounting", "facilities", "customer_service"}
TicketStatus = Literal["open", "in_progress", "waiting_approval", "waiting_customer", "blocked", "resolved"]

# Shop policy (owner's rule, not a database fact): bulk discounts above this
# need a human sign-off, and no quote may go below unit_cost.
MAX_DISCOUNT_WITHOUT_HUMAN_PCT = 15.0
CASH_ACCOUNT = "checking"

mcp = FastMCP(
    "campus-customs",
    instructions=(
        "Tools for the Campus Customs shop database. 'Today' is desk.date_today. "
        "Only report facts these tools return; never invent stock, prices, "
        "vendors, dates, or balances. Payments need a human: agents may only "
        "request_payment; approve_payment / reject_payment are for the human approver."
    ),
)


def date_from(value: str) -> date:
    return date.fromisoformat(value)


def _require_ticket(conn, ticket_id: int) -> dict:
    ticket = row_to_dict(conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone())
    if ticket is None:
        raise ToolError(f"No ticket with id {ticket_id} in the database.")
    return ticket


def _log(conn, ticket_id: int | None, agent: str, entry: str) -> None:
    if ticket_id is not None:
        conn.execute(
            "INSERT INTO ticket_log (ticket_id, agent, entry, created_at) VALUES (?, ?, ?, ?)",
            (ticket_id, agent, entry, now_iso()),
        )


def _cash(conn) -> dict:
    row = conn.execute("SELECT * FROM cash_accounts WHERE name = ?", (CASH_ACCOUNT,)).fetchone()
    if row is None:
        raise ToolError(f"Cash account {CASH_ACCOUNT!r} not found.")
    return dict(row)


def _pending_total(conn) -> float:
    return conn.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_requests WHERE status = 'pending'"
    ).fetchone()[0]


def _open_invoices(conn, vendor_id: int) -> list[dict]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT id, amount, due_date, status, description FROM invoices "
            "WHERE vendor_id = ? AND status = 'open' ORDER BY due_date",
            (vendor_id,),
        )
    ]


# --------------------------------------------------------------------------
# Read tools: the ticket board
# --------------------------------------------------------------------------


@mcp.tool
def list_open_tickets() -> dict:
    """List every ticket on the board that is not resolved, oldest first, with the shop's date_today.

    The Boss starts here to see the whole board before routing work.
    """
    with connect() as conn:
        today = shop_today(conn)
        tickets = [
            dict(r)
            for r in conn.execute(
                "SELECT id, type, requester, subject, sku, size, qty, lease_id, invoice_id, status, created_at "
                "FROM tickets WHERE status != 'resolved' ORDER BY created_at, id"
            )
        ]
    return {"date_today": today.isoformat(), "count": len(tickets), "tickets": tickets}


@mcp.tool(tags={"dashboard"})
def list_tickets() -> dict:
    """List every ticket on the board (open or resolved) with its status, for the dashboard.

    `state` is 'open' until the agent team has made its final call on the ticket
    (status still open / in_progress), then 'resolved'. `status` keeps the Boss's
    exact outcome (resolved, waiting_approval, waiting_customer, blocked) so the
    board can show what, if anything, is left for a human. Also counts pending
    payment requests and saved drafts per ticket.
    """
    with connect() as conn:
        today = shop_today(conn)
        tickets = [
            dict(r)
            for r in conn.execute(
                """SELECT t.id, t.type, t.requester, t.subject, t.sku, t.size, t.qty, t.lease_id, t.invoice_id,
                          t.status, t.notes, t.created_at,
                          (SELECT COUNT(*) FROM payment_requests p WHERE p.ticket_id = t.id AND p.status = 'pending')
                              AS pending_payment_requests,
                          (SELECT COUNT(*) FROM customer_drafts d WHERE d.ticket_id = t.id) AS customer_drafts
                   FROM tickets t ORDER BY t.id"""
            )
        ]
    for t in tickets:
        t["state"] = "open" if t["status"] in ("open", "in_progress") else "resolved"
    return {"date_today": today.isoformat(), "count": len(tickets), "tickets": tickets}


@mcp.tool
def get_ticket(ticket_id: int) -> dict:
    """Read one ticket from the board, with the lease and invoice it links to.

    Returns the ticket row, the shop's date_today, and, when the ticket has a
    lease_id or invoice_id, the full linked lease / invoice (plus the invoice's
    vendor) with days until due or days overdue measured from date_today.
    Also returns the work already done on this ticket: log entries, payment
    requests, purchase orders, stock holds, and customer drafts.
    """
    with connect() as conn:
        today = shop_today(conn)
        ticket = _require_ticket(conn, ticket_id)
        result = {"date_today": today.isoformat(), "ticket": ticket, "lease": None, "invoice": None}

        if ticket["lease_id"] is not None:
            lease = row_to_dict(
                conn.execute("SELECT * FROM leases WHERE id = ?", (ticket["lease_id"],)).fetchone()
            )
            if lease is not None:
                days = (date_from(lease["next_due"]) - today).days
                lease["days_until_due"] = days
                lease["is_overdue"] = days < 0
            result["lease"] = lease

        if ticket["invoice_id"] is not None:
            invoice = row_to_dict(
                conn.execute(
                    """SELECT i.*, v.name AS vendor_name, v.specialty AS vendor_specialty,
                              v.lead_days AS vendor_lead_days
                       FROM invoices i JOIN vendors v ON v.id = i.vendor_id
                       WHERE i.id = ?""",
                    (ticket["invoice_id"],),
                ).fetchone()
            )
            if invoice is not None:
                days = (today - date_from(invoice["due_date"])).days
                invoice["days_overdue"] = max(days, 0)
                invoice["is_overdue"] = invoice["status"] == "open" and days > 0
            result["invoice"] = invoice

        result["work_so_far"] = {
            name: [dict(r) for r in conn.execute(f"SELECT * FROM {table} WHERE ticket_id = ? ORDER BY id", (ticket_id,))]
            for name, table in [
                ("log", "ticket_log"),
                ("payment_requests", "payment_requests"),
                ("purchase_orders", "purchase_orders"),
                ("stock_holds", "stock_holds"),
                ("customer_drafts", "customer_drafts"),
            ]
        }
        return result


# --------------------------------------------------------------------------
# Read tools: stock, vendors, space, money
# --------------------------------------------------------------------------


@mcp.tool
def check_stock(sku: str, size: str | None = None, qty_needed: int | None = None) -> dict:
    """Check stock for a SKU (optionally one size) and compare it to a requested quantity.

    Returns every size on hand for the SKU, the unit_cost and list_price from
    pricing, and, when size and qty_needed are given, how many can ship now
    and the shortfall (qty_needed minus qty on hand, never below 0).
    """
    with connect() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY rowid",
                (sku,),
            )
        ]
        if not rows:
            raise ToolError(f"SKU {sku!r} is not in inventory.")
        pricing = row_to_dict(
            conn.execute("SELECT unit_cost, list_price FROM pricing WHERE sku = ?", (sku,)).fetchone()
        )

    result = {
        "sku": sku,
        "name": rows[0]["name"],
        "sizes_on_hand": [{k: r[k] for k in ("size", "qty", "location")} for r in rows],
        "pricing": None,
    }
    if pricing is not None:
        result["pricing"] = {
            **pricing,
            "unit_margin": round(pricing["list_price"] - pricing["unit_cost"], 2),
        }

    if size is not None:
        match = next((r for r in rows if r["size"] == size), None)
        if match is None:
            available = ", ".join(r["size"] for r in rows)
            raise ToolError(f"Size {size!r} not stocked for {sku}. Sizes in inventory: {available}.")
        result["requested"] = {"size": size, "qty_on_hand": match["qty"]}
        if qty_needed is not None:
            result["requested"].update(
                qty_needed=qty_needed,
                can_fill_now=min(match["qty"], qty_needed),
                shortfall=max(qty_needed - match["qty"], 0),
                in_stock=match["qty"] >= qty_needed,
            )
    return result


@mcp.tool
def check_vendor_status(vendor_id: int | None = None) -> dict:
    """Show vendors, their lead times, and whether they are blocked by an unpaid invoice.

    Shop rule: a vendor will not ship new product while it has an open unpaid
    invoice. For each vendor this returns specialty, lead_days, every open
    invoice (with days overdue from date_today), can_ship, and, if it can ship,
    the earliest arrival date for an order placed today (date_today + lead_days).
    Leave vendor_id empty to see all vendors and pick who can restock.
    """
    with connect() as conn:
        today = shop_today(conn)
        if vendor_id is None:
            vendors = [dict(r) for r in conn.execute("SELECT * FROM vendors ORDER BY id")]
        else:
            row = conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone()
            if row is None:
                raise ToolError(f"No vendor with id {vendor_id} in the database.")
            vendors = [dict(row)]

        for v in vendors:
            open_invoices = _open_invoices(conn, v["id"])
            for inv in open_invoices:
                inv["days_overdue"] = max((today - date_from(inv["due_date"])).days, 0)
            v["open_invoices"] = open_invoices
            v["open_balance"] = round(sum(inv["amount"] for inv in open_invoices), 2)
            v["can_ship"] = not open_invoices
            v["earliest_arrival_if_ordered_today"] = (
                (today + timedelta(days=v["lead_days"])).isoformat() if v["can_ship"] else None
            )
            if not v["can_ship"]:
                ids = ", ".join(f"#{inv['id']}" for inv in open_invoices)
                v["blocked_reason"] = f"Open unpaid invoice(s) {ids} must be paid before this vendor ships."

    return {"date_today": today.isoformat(), "vendors": vendors}


@mcp.tool
def get_lease(lease_id: int) -> dict:
    """Read one lease: space, landlord, monthly_rent, next_due, and days until due from date_today.

    Also reports whether a rent payment for this due date is already pending or paid,
    so Facilities never asks for the same month's rent twice.
    """
    with connect() as conn:
        today = shop_today(conn)
        lease = row_to_dict(conn.execute("SELECT * FROM leases WHERE id = ?", (lease_id,)).fetchone())
        if lease is None:
            raise ToolError(f"No lease with id {lease_id} in the database.")
        days = (date_from(lease["next_due"]) - today).days
        lease.update(days_until_due=days, is_overdue=days < 0)
        lease["rent_requests"] = [
            dict(r)
            for r in conn.execute(
                "SELECT id, amount, status, created_at, decided_by FROM payment_requests "
                "WHERE kind = 'rent' AND ref_id = ? ORDER BY id",
                (lease_id,),
            )
        ]
    return {"date_today": today.isoformat(), "lease": lease}


@mcp.tool
def get_cash_position() -> dict:
    """Show cash on hand and every claim on it.

    Returns the checking balance, payment requests still waiting for a human
    (pending_total), available_to_commit (balance minus pending), open vendor
    invoices, and lease rent coming due. Cash only goes out in this shop; there
    is no revenue, so available_to_commit is the hard ceiling for new requests.
    """
    with connect() as conn:
        today = shop_today(conn)
        cash = _cash(conn)
        pending = [
            dict(r)
            for r in conn.execute(
                "SELECT id, kind, ref_id, amount, payee, ticket_id, requested_by, created_at "
                "FROM payment_requests WHERE status = 'pending' ORDER BY id"
            )
        ]
        pending_total = round(sum(p["amount"] for p in pending), 2)
        invoices = [
            dict(r)
            for r in conn.execute(
                "SELECT i.id, i.vendor_id, v.name AS vendor_name, i.amount, i.due_date, i.description "
                "FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.status = 'open' ORDER BY i.due_date"
            )
        ]
        for inv in invoices:
            inv["days_overdue"] = max((today - date_from(inv["due_date"])).days, 0)
        rent = [
            dict(r)
            for r in conn.execute("SELECT id, space_name, landlord, monthly_rent, next_due FROM leases ORDER BY next_due")
        ]
        for lease in rent:
            lease["days_until_due"] = (date_from(lease["next_due"]) - today).days

    return {
        "date_today": today.isoformat(),
        "account": cash["name"],
        "balance": cash["balance"],
        "balance_as_of": cash["date"],
        "pending_requests": pending,
        "pending_total": pending_total,
        "available_to_commit": round(cash["balance"] - pending_total, 2),
        "open_invoices": invoices,
        "rent_due": rent,
    }


@mcp.tool
def quote_bulk_price(
    sku: str,
    qty: Annotated[int, Field(gt=0)],
    discount_pct: Annotated[float, Field(ge=0, lt=100)] = 0.0,
) -> dict:
    """Price a bulk order at a given discount and check the margin, using pricing.unit_cost / list_price.

    Returns the discounted unit price, order total, unit margin, margin percent,
    and the deepest discount that still covers unit_cost. Refuses any discount
    that would sell below cost. Flags needs_human_signoff when discount_pct is
    above the shop's 15% limit for agent-approved discounts.
    """
    with connect() as conn:
        pricing = row_to_dict(conn.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone())
    if pricing is None:
        raise ToolError(f"No pricing row for SKU {sku!r}.")

    cost, listp = pricing["unit_cost"], pricing["list_price"]
    unit_price = round(listp * (1 - discount_pct / 100), 2)
    break_even_pct = round((1 - cost / listp) * 100, 2)
    if unit_price < cost:
        raise ToolError(
            f"A {discount_pct}% discount prices {sku} at ${unit_price}, below unit_cost ${cost}. "
            f"The deepest discount that still covers cost is {break_even_pct}%."
        )
    unit_margin = round(unit_price - cost, 2)
    return {
        "sku": sku,
        "qty": qty,
        "unit_cost": cost,
        "list_price": listp,
        "discount_pct": discount_pct,
        "unit_price": unit_price,
        "order_total": round(unit_price * qty, 2),
        "list_total": round(listp * qty, 2),
        "customer_saves": round((listp - unit_price) * qty, 2),
        "unit_margin": unit_margin,
        "margin_pct_of_price": round(unit_margin / unit_price * 100, 2) if unit_price else 0.0,
        "order_margin": round(unit_margin * qty, 2),
        "break_even_discount_pct": break_even_pct,
        "max_discount_without_human_pct": MAX_DISCOUNT_WITHOUT_HUMAN_PCT,
        "needs_human_signoff": discount_pct > MAX_DISCOUNT_WITHOUT_HUMAN_PCT,
    }


@mcp.tool
def list_payment_requests(status: Literal["pending", "paid", "rejected", "refused", "all"] = "pending") -> dict:
    """List payment requests (default: those still waiting for a human decision)."""
    with connect() as conn:
        sql = "SELECT * FROM payment_requests"
        args: tuple = ()
        if status != "all":
            sql += " WHERE status = ?"
            args = (status,)
        rows = [dict(r) for r in conn.execute(sql + " ORDER BY id", args)]
    return {"status": status, "count": len(rows), "requests": rows}


# --------------------------------------------------------------------------
# Write tools for agents (no money moves here)
# --------------------------------------------------------------------------


@mcp.tool
def log_ticket_note(ticket_id: int, agent: AgentName, note: str) -> dict:
    """Add a short note to a ticket's work log (what you checked, found, or decided)."""
    conn = connect(readonly=False)
    try:
        _require_ticket(conn, ticket_id)
        _log(conn, ticket_id, agent, note)
    finally:
        conn.close()
    return {"ok": True, "ticket_id": ticket_id, "agent": agent}


@mcp.tool
def set_ticket_status(ticket_id: int, status: TicketStatus, agent: AgentName, reason: str) -> dict:
    """Move a ticket to a new status and log why. The Boss makes these final calls.

    Statuses: open, in_progress, waiting_approval (payment request waiting for a
    human), waiting_customer (draft reply/quote ready), blocked (cannot proceed:
    cash or vendor), resolved (nothing left to do).
    """
    conn = connect(readonly=False)
    try:
        ticket = _require_ticket(conn, ticket_id)
        conn.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))
        _log(conn, ticket_id, agent, f"status {ticket['status']} -> {status}: {reason}")
    finally:
        conn.close()
    return {"ok": True, "ticket_id": ticket_id, "old_status": ticket["status"], "new_status": status}


@mcp.tool
def hold_stock(ticket_id: int, sku: str, size: str, qty: Annotated[int, Field(gt=0)], agent: AgentName) -> dict:
    """Set aside units that are on the shelf for a ticket (inventory.qty goes down, a hold is recorded).

    Refuses to hold more than is on hand. Holds can be undone with release_stock_hold.
    """
    conn = connect(readonly=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        _require_ticket(conn, ticket_id)
        row = conn.execute("SELECT qty FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone()
        if row is None:
            raise ToolError(f"{sku} size {size} is not in inventory.")
        if qty > row["qty"]:
            raise ToolError(f"Only {row['qty']} of {sku} size {size} on hand; cannot hold {qty}.")
        conn.execute("UPDATE inventory SET qty = qty - ? WHERE sku = ? AND size = ?", (qty, sku, size))
        cur = conn.execute(
            "INSERT INTO stock_holds (ticket_id, sku, size, qty, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, sku, size, qty, agent, now_iso()),
        )
        _log(conn, ticket_id, agent, f"held {qty} x {sku} {size} (hold #{cur.lastrowid})")
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {"hold_id": cur.lastrowid, "sku": sku, "size": size, "qty": qty, "qty_left_on_shelf": row["qty"] - qty}


@mcp.tool
def release_stock_hold(hold_id: int, agent: AgentName, reason: str) -> dict:
    """Put held units back on the shelf (inventory.qty goes back up)."""
    conn = connect(readonly=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        hold = row_to_dict(conn.execute("SELECT * FROM stock_holds WHERE id = ?", (hold_id,)).fetchone())
        if hold is None or hold["status"] != "held":
            raise ToolError(f"Hold #{hold_id} does not exist or was already released.")
        conn.execute(
            "UPDATE inventory SET qty = qty + ? WHERE sku = ? AND size = ?", (hold["qty"], hold["sku"], hold["size"])
        )
        conn.execute("UPDATE stock_holds SET status = 'released' WHERE id = ?", (hold_id,))
        _log(conn, hold["ticket_id"], agent, f"released hold #{hold_id}: {reason}")
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {"ok": True, "hold_id": hold_id, "returned_qty": hold["qty"]}


@mcp.tool
def draft_purchase_order(
    ticket_id: int,
    vendor_id: int,
    sku: str,
    size: str,
    qty: Annotated[int, Field(gt=0)],
    agent: AgentName,
) -> dict:
    """Draft a restock purchase order. Cost comes from pricing.unit_cost; nothing is ordered or paid yet.

    The PO becomes an order only when Accounting requests payment and a human
    approves it. The result says whether the vendor is currently blocked by an
    open invoice and the arrival date if it were ordered today.
    """
    conn = connect(readonly=False)
    try:
        _require_ticket(conn, ticket_id)
        today = shop_today(conn)
        vendor = row_to_dict(conn.execute("SELECT * FROM vendors WHERE id = ?", (vendor_id,)).fetchone())
        if vendor is None:
            raise ToolError(f"No vendor with id {vendor_id} in the database.")
        if conn.execute("SELECT 1 FROM inventory WHERE sku = ? AND size = ?", (sku, size)).fetchone() is None:
            raise ToolError(f"{sku} size {size} is not a product the shop stocks.")
        pricing = conn.execute("SELECT unit_cost FROM pricing WHERE sku = ?", (sku,)).fetchone()
        if pricing is None:
            raise ToolError(f"No pricing row for SKU {sku!r}; cannot cost a purchase order.")
        total = round(pricing["unit_cost"] * qty, 2)
        cur = conn.execute(
            "INSERT INTO purchase_orders (vendor_id, sku, size, qty, unit_cost, total, ticket_id, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (vendor_id, sku, size, qty, pricing["unit_cost"], total, ticket_id, agent, now_iso()),
        )
        _log(conn, ticket_id, agent, f"drafted PO #{cur.lastrowid}: {qty} x {sku} {size} from {vendor['name']} = ${total}")
        blocking = _open_invoices(conn, vendor_id)
    finally:
        conn.close()
    return {
        "po_id": cur.lastrowid,
        "status": "draft",
        "vendor": vendor["name"],
        "sku": sku,
        "size": size,
        "qty": qty,
        "unit_cost": pricing["unit_cost"],
        "total": total,
        "vendor_can_ship": not blocking,
        "blocking_invoices": blocking,
        "arrival_if_ordered_today": (today + timedelta(days=vendor["lead_days"])).isoformat(),
    }


@mcp.tool
def request_payment(
    kind: Literal["invoice", "rent", "purchase_order"],
    ref_id: int,
    ticket_id: int,
    reason: str,
    agent: AgentName,
) -> dict:
    """Ask a human to approve a payment. No money moves until a human approves it.

    kind/ref_id: 'invoice' + invoices.id, 'rent' + leases.id, or
    'purchase_order' + purchase_orders.id. The amount and payee are looked up
    from that record; you cannot type an amount. Refused if the item is already
    paid or already waiting for approval, or if the amount is more than
    available_to_commit (balance minus other pending requests), because cash
    can never go negative.
    """
    conn = connect(readonly=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        _require_ticket(conn, ticket_id)
        note = None
        if kind == "invoice":
            inv = row_to_dict(
                conn.execute(
                    "SELECT i.*, v.name AS vendor_name FROM invoices i JOIN vendors v ON v.id = i.vendor_id WHERE i.id = ?",
                    (ref_id,),
                ).fetchone()
            )
            if inv is None:
                raise ToolError(f"No invoice #{ref_id}.")
            if inv["status"] != "open":
                raise ToolError(f"Invoice #{ref_id} is {inv['status']}, not open; nothing to pay.")
            amount, payee = inv["amount"], inv["vendor_name"]
        elif kind == "rent":
            lease = row_to_dict(conn.execute("SELECT * FROM leases WHERE id = ?", (ref_id,)).fetchone())
            if lease is None:
                raise ToolError(f"No lease #{ref_id}.")
            amount, payee = lease["monthly_rent"], lease["landlord"]
            note = f"rent for period due {lease['next_due']}"
        else:
            po = row_to_dict(
                conn.execute(
                    "SELECT p.*, v.name AS vendor_name FROM purchase_orders p JOIN vendors v ON v.id = p.vendor_id WHERE p.id = ?",
                    (ref_id,),
                ).fetchone()
            )
            if po is None:
                raise ToolError(f"No purchase order #{ref_id}.")
            if po["status"] != "draft":
                raise ToolError(f"PO #{ref_id} is {po['status']}; only draft POs can be sent for payment.")
            unqueued = [
                inv["id"]
                for inv in _open_invoices(conn, po["vendor_id"])
                if not conn.execute(
                    "SELECT 1 FROM payment_requests WHERE kind = 'invoice' AND ref_id = ? AND status = 'pending'",
                    (inv["id"],),
                ).fetchone()
            ]
            if unqueued:
                raise ToolError(
                    f"{po['vendor_name']} will not ship while invoice(s) {unqueued} are unpaid. "
                    "Request payment for those invoices first."
                )
            amount, payee = po["total"], po["vendor_name"]

        dup = conn.execute(
            "SELECT id, status FROM payment_requests WHERE kind = ? AND ref_id = ? AND status IN ('pending', 'paid')",
            (kind, ref_id),
        ).fetchone()
        if dup and not (kind == "rent" and dup["status"] == "paid"):
            raise ToolError(f"A {kind} payment for #{ref_id} is already {dup['status']} (request #{dup['id']}).")
        if kind == "rent" and conn.execute(
            "SELECT 1 FROM payment_requests WHERE kind = 'rent' AND ref_id = ? AND status = 'pending'", (ref_id,)
        ).fetchone():
            raise ToolError(f"Rent for lease #{ref_id} is already waiting for approval.")

        balance = _cash(conn)["balance"]
        pending = _pending_total(conn)
        available = round(balance - pending, 2)
        if amount > available:
            raise ToolError(
                f"Refused: ${amount:.2f} to {payee} is more than available_to_commit ${available:.2f} "
                f"(balance ${balance:.2f} minus ${pending:.2f} already pending). Cash cannot go negative."
            )

        full_reason = f"{reason} ({note})" if note else reason
        cur = conn.execute(
            "INSERT INTO payment_requests (kind, ref_id, amount, payee, account, ticket_id, reason, requested_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, payee, CASH_ACCOUNT, ticket_id, full_reason, agent, now_iso()),
        )
        _log(conn, ticket_id, agent, f"requested human approval: pay ${amount:.2f} to {payee} ({kind} #{ref_id}), request #{cur.lastrowid}")
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {
        "request_id": cur.lastrowid,
        "status": "pending",
        "kind": kind,
        "ref_id": ref_id,
        "amount": amount,
        "payee": payee,
        "needs": "human approval (approve_payment) before any money moves",
        "available_to_commit_after": round(available - amount, 2),
    }


@mcp.tool
def save_customer_draft(ticket_id: int, recipient: str, subject: str, body: str, agent: AgentName) -> dict:
    """Save a customer message as a draft on the board. Nothing is emailed or sent."""
    conn = connect(readonly=False)
    try:
        _require_ticket(conn, ticket_id)
        cur = conn.execute(
            "INSERT INTO customer_drafts (ticket_id, recipient, subject, body, author, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (ticket_id, recipient, subject, body, agent, now_iso()),
        )
        _log(conn, ticket_id, agent, f"saved customer draft #{cur.lastrowid} to {recipient} (not sent)")
    finally:
        conn.close()
    return {"draft_id": cur.lastrowid, "status": "draft", "sent": False}


# --------------------------------------------------------------------------
# Human-only tools: the backend never hands these to an agent
# --------------------------------------------------------------------------


@mcp.tool(tags={"human_only"})
def approve_payment(request_id: int, approved_by: str) -> dict:
    """HUMAN ONLY. Approve a pending payment request and pay it from checking.

    Re-checks cash at the moment of payment and refuses (status 'refused') if
    the balance would go negative. On success: inserts a payments row with
    approved_by, lowers cash_accounts.balance, and updates the paid item:
    invoice -> status 'paid'; rent -> lease next_due moves forward one month;
    purchase_order -> status 'ordered' with expected_arrival = date_today + vendor lead_days.
    """
    approver = approved_by.strip()
    if not approver or approver.lower() in AGENT_NAMES:
        raise ToolError("approve_payment needs the name of the human approver, not an agent.")

    conn = connect(readonly=False)
    try:
        conn.execute("BEGIN IMMEDIATE")
        req = row_to_dict(conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone())
        if req is None:
            raise ToolError(f"No payment request #{request_id}.")
        if req["status"] != "pending":
            raise ToolError(f"Request #{request_id} is already {req['status']}.")

        today = shop_today(conn)
        cash = _cash(conn)
        refusal = None
        if req["amount"] > cash["balance"]:
            refusal = f"insufficient funds: ${req['amount']:.2f} requested, ${cash['balance']:.2f} in {cash['name']}"
        elif req["kind"] == "invoice":
            inv = conn.execute("SELECT status FROM invoices WHERE id = ?", (req["ref_id"],)).fetchone()
            if inv is None or inv["status"] != "open":
                refusal = f"invoice #{req['ref_id']} is no longer open"
        elif req["kind"] == "purchase_order":
            po = conn.execute("SELECT * FROM purchase_orders WHERE id = ?", (req["ref_id"],)).fetchone()
            if po is None or po["status"] != "draft":
                refusal = f"PO #{req['ref_id']} is not a draft"
            elif _open_invoices(conn, po["vendor_id"]):
                refusal = "vendor still has an open unpaid invoice; approve that invoice payment first"

        if refusal:
            conn.execute(
                "UPDATE payment_requests SET status = 'refused', decided_by = ?, decided_at = ?, decision_note = ? WHERE id = ?",
                (approver, now_iso(), refusal, request_id),
            )
            _log(conn, req["ticket_id"], "pay_tool", f"refused request #{request_id}: {refusal}")
            conn.execute("COMMIT")
            return {"request_id": request_id, "ticket_id": req["ticket_id"], "status": "refused", "reason": refusal,
                    "balance": cash["balance"]}

        new_balance = round(cash["balance"] - req["amount"], 2)
        pay = conn.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) VALUES (?, ?, ?, ?, ?, ?)",
            (req["kind"], req["ref_id"], req["amount"], cash["name"], today.isoformat(), approver),
        )
        conn.execute(
            "UPDATE cash_accounts SET balance = ?, date = ? WHERE name = ?", (new_balance, today.isoformat(), cash["name"])
        )
        effect: dict = {}
        if req["kind"] == "invoice":
            conn.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (req["ref_id"],))
            effect = {"invoice_id": req["ref_id"], "invoice_status": "paid"}
        elif req["kind"] == "rent":
            lease = conn.execute("SELECT next_due FROM leases WHERE id = ?", (req["ref_id"],)).fetchone()
            new_due = add_one_month(date_from(lease["next_due"])).isoformat()
            conn.execute("UPDATE leases SET next_due = ? WHERE id = ?", (new_due, req["ref_id"]))
            effect = {"lease_id": req["ref_id"], "paid_period_due": lease["next_due"], "next_due": new_due}
        else:
            lead = conn.execute(
                "SELECT v.lead_days FROM purchase_orders p JOIN vendors v ON v.id = p.vendor_id WHERE p.id = ?",
                (req["ref_id"],),
            ).fetchone()["lead_days"]
            arrival = (today + timedelta(days=lead)).isoformat()
            conn.execute(
                "UPDATE purchase_orders SET status = 'ordered', expected_arrival = ? WHERE id = ?", (arrival, req["ref_id"])
            )
            effect = {"po_id": req["ref_id"], "po_status": "ordered", "expected_arrival": arrival}

        conn.execute(
            "UPDATE payment_requests SET status = 'paid', decided_by = ?, decided_at = ?, payment_id = ? WHERE id = ?",
            (approver, now_iso(), pay.lastrowid, request_id),
        )
        _log(conn, req["ticket_id"], "pay_tool", f"paid request #{request_id}: ${req['amount']:.2f} to {req['payee']}, approved by {approver}")
        conn.execute("COMMIT")
    except Exception:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
    return {
        "request_id": request_id,
        "ticket_id": req["ticket_id"],
        "status": "paid",
        "payment_id": pay.lastrowid,
        "amount": req["amount"],
        "payee": req["payee"],
        "approved_by": approver,
        "balance_before": cash["balance"],
        "balance_after": new_balance,
        **effect,
    }


@mcp.tool(tags={"human_only"})
def reject_payment(request_id: int, rejected_by: str, reason: str) -> dict:
    """HUMAN ONLY. Reject a pending payment request. No money moves."""
    approver = rejected_by.strip()
    if not approver or approver.lower() in AGENT_NAMES:
        raise ToolError("reject_payment needs the name of the human, not an agent.")
    conn = connect(readonly=False)
    try:
        req = row_to_dict(conn.execute("SELECT * FROM payment_requests WHERE id = ?", (request_id,)).fetchone())
        if req is None or req["status"] != "pending":
            raise ToolError(f"Request #{request_id} does not exist or is not pending.")
        conn.execute(
            "UPDATE payment_requests SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? WHERE id = ?",
            (approver, now_iso(), reason, request_id),
        )
        _log(conn, req["ticket_id"], "human", f"rejected request #{request_id}: {reason}")
    finally:
        conn.close()
    return {"request_id": request_id, "ticket_id": req["ticket_id"], "status": "rejected", "rejected_by": approver}


ensure_schema()

if __name__ == "__main__":
    mcp.run()
