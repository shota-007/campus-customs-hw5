# Shoreline Desk: Campus Customs dashboard

React + Vite + TypeScript board for the Campus Customs agent crew.

```bash
npm install
npm run dev        # http://localhost:5173 (Vite picks the next port if 5173 is busy)
```

It talks to the FastAPI backend at `http://localhost:8000`. Start that first from `backend/` with `uvicorn main:app --reload --port 8000`. To point somewhere else, copy `.env.example` to `.env.local` and set `VITE_API_URL`.

| File | What it does |
|---|---|
| `src/api.ts` | Typed client for every backend route |
| `src/useDesk.ts` | Polling: fast while a run is live, slow when idle; incremental events; per-run feed + crew activity |
| `src/agents.tsx` | The crew: names, colors, and SVG mascots (turtle, octopus, pelican, hermit crab, dolphin) |
| `src/components/` | Header, CashTide, TicketPostcards, TicketStage (+ Captain's log), CrewRadio, ApprovalInbox, CrewRoster, Bottles, Scenery, Toasts |

Design notes: `../output/design.md`.
