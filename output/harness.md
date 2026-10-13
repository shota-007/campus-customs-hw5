# Campus Customs — Agent Harness

This is the complete harness for **Campus Customs Multi-Agent Operations**. It covers:
- **the data:** the shop tables and the work tables;
- **the MCP server:** 18 tools, the only door to shop data;
- **the agents:** five PydanticAI agents on `gpt-6-luna` via Portkey;
- **the backend:** FastAPI routes;
- **the dashboard:** React, "Shoreline Desk";
- **the safety rules:** the guardrails and token limits that hold it all together.

```
React dashboard (frontend/) ──HTTP──► FastAPI (backend/main.py) ──► Agent team (backend/team.py)
                                              │                              │
                                              └──── MCP (stdio) ─────────────┘
                                                        │
                                              mcp_server/server.py ──► data/campus_customs_new.db
```

## Contents
1. [Runbook](#1-runbook)
2. [Shop rules and where they are enforced](#2-shop-rules-and-where-they-are-enforced)
3. [Data: tables](#3-data-tables)
4. [The three tickets](#4-the-three-tickets)
5. [MCP tools](#5-mcp-tools-mcp_serverserverpy)
6. [The five agents](#6-the-five-agents-backend)
7. [Backend API routes](#7-backend-api-routes-backendmainpy-fastapi)
8. [Dashboard](#8-dashboard-frontend-react--vite--typescript)
9. [Safety: guardrails and token limits](#9-safety-guardrails-and-token-limits)
10. [Full run results and known gaps](#10-full-run-results-problem-9-and-known-gaps)
11. [Evidence files](#11-evidence-files)

---

## 1. Runbook

```bash
# once
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cd frontend && npm install && cd ..
# PORTKEY_API_KEY lives in .env (project root or the course root above it)

# backend: http://localhost:8000 (docs at /docs)
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000

# dashboard: http://localhost:5173 (Vite picks the next free port if busy)
cd frontend && npm run dev
```

**Full run:**
1. Click **🌅 New day** (`POST /reset`) so the working DB is a fresh copy of the original.
2. Note the opening balance in The Tide.
3. Pick a ticket and click **🏄 Send the crew** (`POST /tickets/{id}/run`).
4. Review the request in **Needs your OK** and approve or decline (`POST /payments/{id}/approve`).
5. Repeat for each ticket.

**Command-line alternatives:**
- `python -m backend.run_tickets`: reset, Boss triage, then every open ticket.
- `python -m backend.reset_db`: reset only.

---

## 2. Shop rules and where they are enforced

| Shop rule | Enforced in code by |
|---|---|
| `desk.date_today` is "today" | Every date calculation goes through `shop_today()` in `mcp_server/db.py`; tools return `days_until_due` / `days_overdue` from it |
| Vendor lead times come from `vendors` | `check_vendor_status` / `draft_purchase_order` compute arrival = `date_today + lead_days`; prompts forbid other dates |
| No shipping while a vendor has an open unpaid invoice | `check_vendor_status.can_ship`; `request_payment` refuses a PO while the vendor's invoice is unqueued; `approve_payment` refuses a PO while the invoice is still open |
| Human approval for every payment | Agents only get `request_payment`; `approve_payment` is human-only (filtered per role, blocked again in `mcp_link._guard_tool_call`), requires a named human, and writes `payments.approved_by` |
| If there isn't enough cash, the pay tool refuses | `request_payment` refuses amounts above `available_to_commit`; `approve_payment` re-checks the balance and marks the request `refused` |
| Cash only goes out | No tool adds money; `cash_accounts.balance` only decreases in `approve_payment` |
| Reset before a full run | `POST /reset` / **New day** / `python -m backend.reset_db` copy the original over the working copy |
| No emailing customers or calling vendors | No email, SMS, or HTTP tools exist; `save_customer_draft` stores drafts on the board, `sent: false` |
| Only `gpt-6-luna` via Portkey | One `MODEL_NAME`; every response's served model is checked; `ModelMismatchError` stops the run otherwise |
| Never invent data | Tools return DB values or raise an error; agents can't type amounts; reports cite `source_tool` for every fact |

---

## 3. Data: tables

- **Original DB (never modified):** `data/campus_customs.db`
- **Working copy (agents read and write this):** `data/campus_customs_new.db`
- **Reset:** copy the original over the working copy before every full run. The audit trail is not reset.

### 3a. Shop tables (from the original database)

#### `desk`
| Field | Type | Notes |
|---|---|---|
| `date_today` | TEXT | The shop's "today" (`2026-08-31`) |
| `notes` | TEXT | Free-form desk notes |

**Why it matters:** this is the shop's clock. Every overdue or due-soon decision compares against `date_today`, never the real date.

#### `tickets`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Ticket number |
| `type` | TEXT | `customer_order`, `rent_notice`, `price_override`, … |
| `requester` | TEXT | Who asked (customer, landlord, student org) |
| `subject` | TEXT | Short title |
| `sku` | TEXT | Product involved → `inventory.sku`, `pricing.sku` |
| `size` | TEXT | Size involved → `inventory.size` |
| `qty` | INTEGER | Units requested |
| `lease_id` | INTEGER FK | → `leases.id` |
| `invoice_id` | INTEGER FK | → `invoices.id` |
| `status` | TEXT | `open` → the Boss's final call: `waiting_approval` / `waiting_customer` / `blocked` / `resolved` |
| `notes` | TEXT | Request details in the requester's words |
| `created_at` | TEXT | ISO timestamp |

**Why it matters:** this is the work queue. The Boss reads each open ticket and routes it, and the linked columns (`sku`/`size`, `lease_id`, `invoice_id`) tell it which specialist agents to involve.

#### `inventory`
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT PK (with size) | Product code |
| `name` | TEXT | Product name |
| `size` | TEXT PK (with sku) | `S`/`M`/`L`/`XL` or `OS` (one size) |
| `qty` | INTEGER | Units on hand (stock holds subtract from this) |
| `location` | TEXT | Aisle |

**Why it matters:** the Inventory agent checks stock by SKU and size here to decide whether an order can ship now or there's a shortfall to restock.

#### `pricing`
| Field | Type | Notes |
|---|---|---|
| `sku` | TEXT PK | Product code (no size suffix) |
| `unit_cost` | REAL | What the shop pays per unit |
| `list_price` | REAL | What the customer pays per unit |

**Why it matters:** Accounting uses it to check margins on discount requests, and restock purchase orders are costed from it (qty × `unit_cost`).

#### `vendors`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Vendor id |
| `name` | TEXT | Vendor name |
| `specialty` | TEXT | What they supply (apparel reprint, mugs, courier) |
| `lead_days` | INTEGER | Days from order to delivery |

**Why it matters:** Inventory picks the restock vendor by `specialty` and estimates the arrival date from `lead_days`.

#### `leases`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Lease id |
| `space_name` | TEXT | The space being rented |
| `landlord` | TEXT | Who gets paid |
| `monthly_rent` | REAL | Rent amount |
| `next_due` | TEXT | Next rent due date (moves forward a month when rent is paid) |
| `notes` | TEXT | Lease notes |

**Why it matters:** Facilities uses it to confirm rent notices (amount, landlord, due date).

#### `cash_accounts`
| Field | Type | Notes |
|---|---|---|
| `name` | TEXT PK | Account name (`checking`) |
| `balance` | REAL | Current cash |
| `date` | TEXT | As-of date |

**Why it matters:** this is the only source of money. It's checked before any payment, and the pay tool refuses anything that would make the balance negative. Cash only goes out.

#### `payments`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Payment id |
| `kind` | TEXT | `invoice`, `rent`, `purchase_order` |
| `ref_id` | INTEGER | Id of the invoice, lease, or PO that was paid |
| `amount` | REAL | Amount paid |
| `account` | TEXT | Which `cash_accounts.name` it came from |
| `paid_at` | TEXT | Shop date it was paid |
| `approved_by` | TEXT | The human who approved it |

**Why it matters:** this is the money audit trail. Only `approve_payment` writes here, and `approved_by` is proof a human signed off.

#### `invoices`
| Field | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | Invoice id |
| `vendor_id` | INTEGER FK | → `vendors.id` |
| `amount` | REAL | Amount owed |
| `due_date` | TEXT | When it's due |
| `status` | TEXT | `open` / `paid` |
| `description` | TEXT | What it was for |

**Why it matters:** Accounting tracks what the shop owes here. An `open` invoice blocks that vendor from shipping any new product until it's paid.

### 3b. Work tables (created by the MCP server in the working copy only; a reset wipes them)

| Table | Fields | Written by | Why it exists |
|---|---|---|---|
| `payment_requests` | id, kind, ref_id, amount, payee, account, ticket_id, reason, requested_by, status (`pending`/`paid`/`rejected`/`refused`), created_at, decided_by, decided_at, decision_note, payment_id | `request_payment` (agents); `approve_payment`, `reject_payment` (human) | Separates "an agent asked" from "a human paid" |
| `purchase_orders` | id, vendor_id, sku, size, qty, unit_cost, total, ticket_id, status (`draft`/`ordered`/`cancelled`), created_by, created_at, expected_arrival | `draft_purchase_order`; `approve_payment` sets `ordered` | Restock plans, costed from `pricing` |
| `stock_holds` | id, ticket_id, sku, size, qty, status (`held`/`released`), created_by, created_at | `hold_stock`, `release_stock_hold` | Sets units aside for one ticket so they aren't sold twice |
| `customer_drafts` | id, ticket_id, recipient, subject, body, author, status (`draft`), created_at | `save_customer_draft` | Customer messages stay on the board, never sent |
| `ticket_log` | id, ticket_id, agent, entry, created_at | every write tool + `log_ticket_note` | Per-ticket history of who did what |

### 3c. How the tables connect

```
tickets.sku/size ──► inventory (sku, size) ──► pricing (sku)
tickets.lease_id ──► leases.id
tickets.invoice_id ─► invoices.id ──► vendors.id
payments.ref_id ───► invoices.id | leases.id | purchase_orders.id   (by payments.kind)
payments.account ──► cash_accounts.name
payment_requests.payment_id ──► payments.id        purchase_orders.vendor_id ──► vendors.id
payment_requests / purchase_orders / stock_holds / customer_drafts / ticket_log .ticket_id ──► tickets.id
```

---

## 4. The three tickets

The pre-run analysis (as of 2026-08-31) follows. Expected-vs-actual for each ticket is in `output/desk_tickets.html`.

### Ticket 101: `customer_order` — Tauhid Zaman, Bulldog tee
- **Asks for:** 1 × `CC-TEE-WHITE`, size `S`. Stock S = **0**.
- **Linked invoice:** #501, $840, Bulldog Print Co, "Rush reprint CC-TEE-WHITE S", due 2026-08-28, **3 days overdue**.
- **Chain:** the order needs the reprint, the reprint needs Bulldog to ship, Bulldog won't ship while #501 is unpaid, and paying #501 needs a human and enough cash.

### Ticket 102: `rent_notice` — Elm City Properties, Rent due
- **Asks for:** shop rent, "due in 2 days".
- **Linked lease:** lease #1, Chapel Street shop, **$2,400** to Elm City Properties, due **2026-09-02**. That matches the notice.
- **Chain:** Facilities verifies the lease, then Accounting requests payment, then a human approves, and `next_due` moves to 2026-10-02.

### Ticket 103: `price_override` — Yale AI Club, Bulk hoodie discount
- **Asks for:** 20 × `CC-HOOD-NAVY`, size `M`, at a bulk discount.
- **Stock and pricing:** 8 on hand, so **12 short**. Cost $22, list $58 ($36 margin).
- **Restock:** comes from Bulldog Print Co: 12 × $22 = $264.

### Cross-ticket cash constraint
| Item | Amount | Running balance |
|---|---|---|
| Starting checking | — | $3,400 |
| Invoice #501 (unblocks Bulldog) | −$840 | $2,560 |
| Rent, lease 1 | −$2,400 | $160 |
| Restock 12 hoodies @ $22 | −$264 | **−$104** ✗ refused |

---

## 5. MCP tools (`mcp_server/server.py`)

FastMCP server over stdio, registered for the vibe coder in `.mcp.json` and started by the backend through `backend/mcp_link.py`. It is the **only** way agents and the dashboard reach shop data.

| # | Tool | Who calls it | Reads | Writes |
|---|---|---|---|---|
| 1 | `list_open_tickets` | Boss | `tickets`, `desk` | — |
| 2 | `list_tickets` | Dashboard (`GET /tickets`) | `tickets`, `desk`, `payment_requests`, `customer_drafts` | — |
| 3 | `get_ticket` | everyone | `tickets`, `desk`, `leases`, `invoices`, `vendors`, + work tables for that ticket | — |
| 4 | `check_stock` | Inventory, Customer Service | `inventory`, `pricing` | — |
| 5 | `check_vendor_status` | Inventory, Accounting | `vendors`, `invoices`, `desk` | — |
| 6 | `get_lease` | Facilities | `leases`, `desk`, `payment_requests` | — |
| 7 | `get_cash_position` | Boss, Accounting, Facilities, Dashboard | `cash_accounts`, `payment_requests`, `invoices`, `vendors`, `leases`, `desk` | — |
| 8 | `quote_bulk_price` | Accounting, Customer Service | `pricing` | — |
| 9 | `list_payment_requests` | Boss, Accounting, Dashboard | `payment_requests` | — |
| 10 | `log_ticket_note` | every agent | `tickets` | `ticket_log` |
| 11 | `set_ticket_status` | Boss | `tickets` | `tickets.status`, `ticket_log` |
| 12 | `hold_stock` | Inventory | `inventory`, `tickets` | `inventory.qty` (−), `stock_holds`, `ticket_log` |
| 13 | `release_stock_hold` | Inventory | `stock_holds` | `inventory.qty` (+), `stock_holds`, `ticket_log` |
| 14 | `draft_purchase_order` | Inventory | `vendors`, `inventory`, `pricing`, `invoices`, `desk` | `purchase_orders`, `ticket_log` |
| 15 | `request_payment` | Accounting | `invoices`, `vendors`, `leases`, `purchase_orders`, `cash_accounts`, `payment_requests` | `payment_requests` (pending), `ticket_log` |
| 16 | `save_customer_draft` | Customer Service | `tickets` | `customer_drafts`, `ticket_log` |
| 17 | `approve_payment` | **Human only** (`POST /payments/{id}/approve`) | `payment_requests`, `cash_accounts`, `invoices`, `purchase_orders`, `vendors`, `desk` | `payments`, `cash_accounts.balance`, `invoices.status`, `leases.next_due`, `purchase_orders.status`, `payment_requests`, `ticket_log` |
| 18 | `reject_payment` | **Human only** (`POST /payments/{id}/reject`) | `payment_requests` | `payment_requests`, `ticket_log` |

**The first three tools (Problem 3), and why:**
- **`get_ticket` unlocks 102.** The notice has no amount; the $2,400, the landlord, and the due date live in `leases`.
- **`check_stock` unlocks 103 (and 101).** It returns the size-M shortfall and the cost/list margin together.
- **`check_vendor_status` unlocks 101 (and the 103 restock).** It applies the open-invoice shipping rule directly.

Payments came later, once a human-approval step and a no-negative-balance check existed. Smoke-test evidence from the vibe coder is in `output/mcp_smoke.json`.

---

## 6. The five agents (`backend/`)

Five PydanticAI agents, all on **`gpt-6-luna` via Portkey**. `backend/config.py` uses the Responses API, because Portkey's deployment only allows tools together with reasoning there; reasoning effort is `low`. Each agent has:
- a detailed prompt in `backend/prompts/<agent>.md`, covering its role, scope, tools, shop rules, playbook, delegation rules, budget discipline, and output contract;
- a typed report in `backend/models.py`, where every report lists its `facts` with the `source_tool` of each;
- an allow-list of MCP tools.

| Agent | Mascot (dashboard) | File | Prompt | Output | MCP tools |
|---|---|---|---|---|---|
| **Boss** | Sea-turtle captain | `backend/agents/boss.py` | `prompts/boss.md` | `BossDecision` / `TriagePlan` | `list_open_tickets`, `get_ticket`, `get_cash_position`, `list_payment_requests`, `log_ticket_note`, `set_ticket_status` |
| **Inventory** | Octopus | `backend/agents/inventory.py` | `prompts/inventory.md` | `InventoryReport` | `get_ticket`, `check_stock`, `check_vendor_status`, `hold_stock`, `release_stock_hold`, `draft_purchase_order`, `log_ticket_note` |
| **Accounting** | Pelican | `backend/agents/accounting.py` | `prompts/accounting.md` | `AccountingReport` | `get_ticket`, `get_cash_position`, `check_vendor_status`, `quote_bulk_price`, `list_payment_requests`, `request_payment`, `log_ticket_note` |
| **Facilities** | Hermit crab | `backend/agents/facilities.py` | `prompts/facilities.md` | `FacilitiesReport` | `get_ticket`, `get_lease`, `get_cash_position`, `log_ticket_note` |
| **Customer Service** | Dolphin | `backend/agents/customer_service.py` | `prompts/customer_service.md` | `CustomerServiceReport` | `get_ticket`, `check_stock`, `quote_bulk_price`, `save_customer_draft`, `log_ticket_note` |

**Full connectivity:** every agent has the same `delegate(to_agent, task)` tool and can hand work to any other agent. The delegate's typed report comes back as the tool result.

**Agent loop and audit** (`backend/team.py`, `backend/audit.py`):
1. Each agent run is driven step by step with `agent.iter`.
2. Every node is appended to `output/audit_trail.json`: the prompt in, the model response out (text, tool calls and arguments, served model, step tokens), the tool results and refusals, delegations, the final output, and errors.
3. Human actions are appended too: approvals, rejections, and resets.
4. The file is append-only.

**Safety net:** if the Boss returns a final decision but forgets `set_ticket_status`, `team._apply_final_status` records it.

---

## 7. Backend API routes (`backend/main.py`, FastAPI)

Start it from `backend/` with `uvicorn main:app --reload --port 8000`. Every route reads and writes through the MCP server. CORS allows the Vite origin (`http://localhost:5173`, plus any localhost port).

- `GET /tickets`: every ticket with its `status` and `state`. `state` is `open` until the crew makes its final call, then `resolved`. The response also carries pending-payment and draft counts, plus the active run.
- `GET /tickets/{ticket_id}`: one ticket, its linked lease or invoice, and all work done on it (log, holds, POs, payment requests, drafts).
- `POST /tickets/{ticket_id}/run`: runs the agent team (Boss first) on that ticket in the background and returns 202 with a `run_id` (`?wait=true` blocks until it finishes). Only one run at a time; a second call gets 409.
- `GET /runs` · `GET /runs/{run_id}`: run status and the Boss's final `BossDecision`.
- `GET /events?after=&limit=&ticket_id=&run_id=&raw=`: recent agent events from the audit trail, condensed into what each agent said, the tools it used, the results, delegations, tokens so far, and human actions.
- `GET /payments?status=`: payment and purchase-order requests (default `pending`).
- `POST /payments/{request_id}/approve` `{"approved_by"}`: **the only route that moves cash.** Calls the human-only `approve_payment`, which re-checks cash and refuses rather than go negative, writes `payments`, lowers the balance, and updates the invoice, lease, or PO.
- `POST /payments/{request_id}/reject` `{"rejected_by", "reason"}`: declines a request; no money moves.
- `GET /cash`: the checking balance from `cash_accounts`, plus pending and `available_to_commit`.
- `POST /reset`: copies the original DB over the working copy (refused during a run). The audit trail is kept.
- `GET /`: health check, agents ready, active run, and the route list.

---

## 8. Dashboard (`frontend/`, React + Vite + TypeScript)

**Shoreline Desk.** Start it with `cd frontend && npm run dev`. It calls `http://localhost:8000`; set `VITE_API_URL` to override. Full design rationale and sources are in `output/design.md`.

| Board requirement | Where it lives |
|---|---|
| List all three tickets | Ticket board: postcards with a type stamp, status, and badges (💸 pending approvals, ✉️ drafts) |
| Pick a ticket and start the team | Ticket stage → **🏄 Send the crew** (one run at a time) |
| Each agent's words and actions while it runs | **Crew Radio**: a live feed (1.5 s polling) of speech bubbles per agent mascot and color, tool chips in plain English that expand to the raw call and result, hand-off cards, nesting by delegation depth, and a "who's doing what" line |
| Ticket marked resolved when the run finishes | A green **RESOLVED** ink stamp plus the outcome ("Awaiting your OK", "Waiting on customer", "Approved · nothing waiting"), and a toast |
| Short summary of what each agent did | **Crew roster** (summary, actions, tools, hand-offs per agent) and the **Captain's log** (Boss decision, needs-you, next-up, blockers, duration, tokens) |
| Human approves a pay or purchase | **Needs your OK** inbox: Approve & pay / Decline with reason, signed with the desk user's name |
| Checking balance that drops after approval | **The Tide**: a big balance that counts down, a tide pool that drains, an "if all approved" line, and paid receipts |

---

## 9. Safety: guardrails and token limits

The prompts tell the agents the rules, but the code enforces them, so a confused or manipulated model still can't break them.

### Guardrails (what a real business would want before agents touch customers and money)

| Guardian | How it's enforced |
|---|---|
| **A human approves every payment** | Agents only have `request_payment`. Only `approve_payment` moves money; it needs a named human (agent names are rejected), is filtered out of every agent's toolset, and is blocked again in `mcp_link._guard_tool_call`. The dashboard requires a name before Approve is enabled. |
| **No negative balance** | `request_payment` refuses anything above `available_to_commit`. `approve_payment` re-checks the live balance and marks the request `refused` instead of paying. |
| **Agents can't type dollar amounts** | The amount and payee are read from the invoice, lease, or PO. |
| **No duplicate payments** | One pending or paid request per invoice or PO; rent can't be requested twice while one is pending; a paid invoice can't be paid again. |
| **Vendor rule** | A PO can't be sent for payment while its vendor has an unqueued open invoice, and can't be approved while that invoice is open. |
| **Every action is attributable** | The `agent` argument on write tools is overwritten with the caller's real role; every write logs to `ticket_log`; every payment records `approved_by`. |
| **Nothing reaches a real customer or vendor** | There are no email, SMS, or HTTP tools; drafts are stored with `sent: false`, and the dashboard labels them "never sent". |
| **No invented data** | Tools return DB values or raise an error; reports cite the `source_tool` of every fact; prompts forbid guessing dates, stock, or prices. |
| **Stock can't be oversold** | `hold_stock` refuses to hold more than is on hand; holds are reversible. |
| **Discount ceiling** | `quote_bulk_price` refuses prices below `unit_cost` and flags discounts over 15% (the owner's policy) for human sign-off. |
| **Atomic money writes** | Payments, holds, and requests run in `BEGIN IMMEDIATE` transactions with rollback. |
| **One run at a time** | `POST /tickets/{id}/run` returns 409 while another run is active, because tickets share the same cash. |
| **Original data is protected** | Only `campus_customs_new.db` is ever opened for writing; reset restores it from the original. |
| **Model lock** | One `MODEL_NAME = "gpt-6-luna"`; the served model is checked on every response (`gpt-6-luna-global` in every run). |
| **Full audit** | Every agent-loop step and human action is appended to `output/audit_trail.json`, which is never wiped. |

### Limits that keep token use in check

| Limit | Value | Where |
|---|---|---|
| Tokens per ticket (Boss + everyone it pulls in, one shared counter) | **150,000** | `TICKET_LIMITS.total_tokens_limit` |
| Model requests per ticket | **30** | `TICKET_LIMITS.request_limit` |
| Tool calls per ticket | **45** | `TICKET_LIMITS.tool_calls_limit` |
| Triage pass | 4 requests / 4 tool calls / 40k tokens | `TRIAGE_LIMITS` |
| Output tokens per response | **1,800**, reasoning effort `low` | `MODEL_SETTINGS` |
| Delegation depth | **2** (Boss → specialist → specialist) | `MAX_DELEGATION_DEPTH` |
| Hand-offs per ticket | **8** | `MAX_DELEGATIONS_PER_TICKET` |
| Loop breakers | No self-delegation, and no delegating back to an agent already waiting in the chain (no A→B→A ping-pong) | `team._delegate` |
| Retries | 2; business refusals come back as tool results, not retry loops | `retries=2`, `tool_error_behavior="failed"` |
| Audit payload size | 4,000 chars per prompt or tool result | `AUDIT_TEXT_LIMIT` |
| Prompt-level discipline | A "Budget discipline" section in every prompt | `backend/prompts/*.md` |

When a ticket hits its budget, the run stops cleanly (`{"stopped": "budget"}`) with an `error` event in the audit trail.

**Measured in the Problem 9 full run:**

| Ticket | Tokens | Requests | Time |
|---|---|---|---|
| 101 | 75,883 | 19 | 33 s |
| 102 | 52,233 | 15 | 27 s |
| 103 | 87,710 | 21 | 48 s |
| **Total** | **215,826** | 55 | |

Every ticket stayed under the 150k cap.

---

## 10. Full run results (Problem 9) and known gaps

**Steps:**
1. Reset with **New day**. Opening checking was **$3,400.00**.
2. Ran 101, 102, and 103 from the dashboard, approving each payment as S.K..

**Results:**

| Ticket | Crew | Final status | Cash |
|---|---|---|---|
| 101 | Boss → Inventory, Accounting, Customer Service | `waiting_approval` → invoice #501 approved | −$840.00 → $2,560.00 |
| 102 | Boss → Facilities → Accounting | `waiting_approval` → rent approved; lease due 2026-10-02 | −$2,400.00 → $160.00 |
| 103 | Boss → Inventory, Accounting, Customer Service | `waiting_customer`; PO #2 ($264) refused by the pay tool | $0.00 → $160.00 |

**Ending checking: $160.00 = `cash_accounts.balance`.** The itemized breakdown is in the Cash tab of `output/desk_tickets.html`.

**Gaps the run exposed (Expected vs Actual):**
- **101:** Inventory drafted PO #1 for 1 tee even though invoice #501 *is* that reprint. It was never funded, but it's a duplicate plan.
- **103:** Accounting called `quote_bulk_price` with SKU `CC-HOOD-NAVY-M` (size glued onto the SKU), so no discount was quoted and the club's actual question went unanswered.
- **All three tickets:** each specialist re-reads `get_ticket` even when the Boss already passed the facts along, which costs tokens.

---

## 11. Evidence files

| File | What it shows |
|---|---|
| `output/audit_trail.json` | Append-only log of every agent-loop step and human action (test runs and the Problem 9 run) |
| `output/desk_tickets.html` | Expected (Problem 6) vs Actual (Problem 9) per ticket, plus the Cash tab |
| `output/resolved_tickets.json` | Per ticket: id, final status, outcome, each agent's contribution, human approvals, refusals, cash change |
| `output/resolved_board.html` | Screenshots of the React board for each resolved ticket (embedded; also `board_101/102/103.jpg`) |
| `output/mcp_smoke.json` | The vibe coder calling the MCP tools (Problem 4) |
| `output/design.md` | Dashboard design choices and references |
| `AI_prompts.md` | What I typed to the vibe coder, per problem |
