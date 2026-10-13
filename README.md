# Campus Customs Multi-Agent Operations (HW5)

A five-agent team runs the Campus Customs shop desk. Open tickets (customer orders, rent, unpaid bills, discount requests) are worked by:
- **Boss:** reads each ticket, routes it, makes the final call.
- **Inventory:** stock, holds, restock vendors, purchase orders.
- **Accounting:** cash, margins, payment requests.
- **Facilities:** leases and rent.
- **Customer Service:** customer drafts, which are never sent.

All shop data flows through an **MCP server**, the agents run inside a **FastAPI** backend, and a **React** dashboard (Shoreline Desk) lets a human watch the agents work and **approve payments**. Agents can only *prepare* a payment; cash moves only when a human approves it.

```
React board (frontend/) ──HTTP──► FastAPI (backend/main.py) ──► 5 PydanticAI agents (backend/team.py)
                                          │                               │
                                          └──────── MCP over stdio ───────┘
                                                        │
                                          mcp_server/server.py ──► data/campus_customs_new.db
```

- **Model:** every agent uses **`gpt-6-luna` via Portkey** (`PORTKEY_API_KEY`), and no other model.
- **Full documentation:** `output/harness.md`, covering the tables, all 18 MCP tools, the agents, routes, dashboard, and safety rules.

---

## Setup (once)

**Requirements:** Python 3.11+, Node 18+.

```bash
git clone https://github.com/shota-007/campus-customs-hw5.git
cd campus-customs-hw5

# Python env: .mcp.json and the commands below expect it at .venv/
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Portkey key: copy the example and paste your own key (the real .env is never committed)
cp .env.example .env

# Dashboard dependencies
cd frontend && npm install && cd ..
```

---

## Run it

### 1. Get a clean working database (whenever you want a fresh run)

The agents only ever read and write the **working copy**. The original stays untouched so you can always reset:

| File | Role |
|---|---|
| `data/campus_customs.db` | The original shop database. Never modified. |
| `data/campus_customs_new.db` | The working copy that the MCP server, agents, and backend use |

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

Equivalent options:
- `.venv/bin/python -m backend.reset_db`
- the dashboard's **🌅 New day** button
- `curl -X POST http://localhost:8000/reset`

> The committed `campus_customs_new.db` is the **end state of my full three-ticket run** (checking $160.00), so the Cash tab in `output/desk_tickets.html` can be checked against it. Reset it before running the tickets yourself.

### 2. Start the MCP server

```bash
.venv/bin/python -m mcp_server.server
```

It speaks MCP over **stdio**, so on its own it just waits for a client. Who starts it in practice:
- **The FastAPI backend** launches its own copies automatically (`backend/mcp_link.py`): one for the agents and one for human/dashboard actions.
- **Claude Code** (the vibe coder) picks it up from `.mcp.json`.

Run it by hand only to test it with an MCP client.

### 3. Start the FastAPI backend: http://localhost:8000

```bash
cd backend
../.venv/bin/uvicorn main:app --reload --port 8000
```

- If your venv is activated, `uvicorn main:app --reload --port 8000` works too.
- Interactive API docs are at http://localhost:8000/docs.
- CORS allows the Vite dashboard origin (`http://localhost:5173`).

### 4. Start the React board: http://localhost:5173

```bash
cd frontend
npm run dev
```

- The board calls the backend at `http://localhost:8000`. To point it elsewhere, copy `frontend/.env.example` to `frontend/.env.local` and set `VITE_API_URL`.
- If port 5173 is busy, Vite uses the next free port; the backend allows any localhost port.

### 5. Full three-ticket run (reset first!)

1. **Reset the database:** click **🌅 New day** on the board (or step 1). Checking should read **$3,400.00** and all three tickets should be open.
2. Type your name in the header. It's recorded as `approved_by` on every payment.
3. For each ticket, **101 → 102 → 103**:
   1. Pick the ticket and click **🏄 Send the crew**.
   2. Watch the Crew Radio until the card is stamped **RESOLVED**.
   3. Review the request in **Needs your OK** and click **Approve & pay** (or **Decline**).
4. Expected money flow:

| Ticket | Payment | Checking after |
|---|---|---|
| 101 | invoice #501, −$840 | $2,560 |
| 102 | rent, −$2,400 | $160 |
| 103 | none: the $264 restock is **refused**, because cash can't go negative | $160 |

**Command-line alternative:** `.venv/bin/python -m backend.run_tickets` resets, lets the Boss triage the board, and works every open ticket. Approvals still happen in the dashboard.

---

## What's where

```
hw5/
├── AI_prompts.md              # what I typed to my vibe coder, per problem
├── README.md
├── requirements.txt
├── .env.example               # PORTKEY_API_KEY=… (real .env is git-ignored)
├── .gitignore
├── .mcp.json                  # registers the MCP server for Claude Code
├── data/
│   ├── campus_customs.db      # original (never modified)
│   └── campus_customs_new.db  # working copy
├── mcp_server/
│   ├── server.py              # 18 FastMCP tools (the only door to shop data)
│   ├── db.py                  # working-DB connection, shop date, work tables
│   └── README.md
├── backend/
│   ├── main.py                # FastAPI routes (tickets, run, events, payments/approve, cash, reset)
│   ├── models.py              # Pydantic data types: agent reports, BossDecision, audit events
│   ├── team.py                # the agent team: delegation, agent loops, budgets
│   ├── agents/                # boss.py, inventory.py, accounting.py, facilities.py, customer_service.py
│   ├── prompts/               # boss.md, inventory.md, accounting.md, facilities.md, customer_service.md
│   ├── audit.py · mcp_link.py · config.py · reset_db.py · run_tickets.py
├── frontend/                  # React + Vite + TypeScript dashboard (Shoreline Desk)
└── output/
    ├── harness.md             # full harness: tables, MCP tools, agents, routes, dashboard, safety
    ├── mcp_smoke.json         # the vibe coder calling the MCP tools
    ├── desk_tickets.html      # Expected vs Actual per ticket + Cash + Reflection tabs
    ├── design.md              # dashboard design choices
    ├── resolved_tickets.json  # per-ticket outcome, agent contributions, human approvals
    ├── resolved_board.html    # screenshots of the board for each resolved ticket
    ├── audit_trail.json       # append-only log of every agent-loop step
    └── github_url.txt
```

## Safety in one glance

- **Payments:** agents can only call `request_payment`, and the amount is read from the invoice, lease, or purchase order. `approve_payment` is human-only and needs a named approver.
- **Cash:** the pay tools refuse anything that would make the balance negative. Cash only goes out.
- **Messages:** nothing is emailed or sent. Customer messages are drafts on the board.
- **Budgets:** each ticket is capped at 150k tokens, 30 model requests, 45 tool calls, delegation depth 2, and 8 hand-offs.
- **Audit:** every agent step and human action is appended to `output/audit_trail.json`.
