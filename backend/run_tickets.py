"""Run the Campus Customs agent team over the ticket board from the command line.

  python -m backend.run_tickets              # reset DB, Boss triages, then works every open ticket
  python -m backend.run_tickets --ticket 102 # work one ticket on the current working DB (no reset)
  python -m backend.run_tickets --no-reset   # full board without resetting first

Agents only *request* payments. Approving them is a human step (dashboard, later problem).
"""

import argparse
import asyncio
import json
import os

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from .reset_db import reset_working_db  # noqa: E402
from .team import CampusCustomsTeam  # noqa: E402


def _show(result) -> None:
    data = result.model_dump(mode="json") if hasattr(result, "model_dump") else result
    print(json.dumps(data, indent=2))


async def main(ticket: int | None, reset: bool) -> None:
    if reset:
        reset_working_db()
        print("Working DB reset from the original.")
    async with CampusCustomsTeam() as team:
        if ticket is not None:
            _show(await team.run_ticket(ticket))
            return
        plan = await team.triage()
        print("Triage plan:")
        _show(plan)
        for item in sorted(plan.items, key=lambda i: i.priority):
            print(f"\n=== Ticket {item.ticket_id} ===")
            _show(await team.run_ticket(item.ticket_id, board_note=f"priority {item.priority}: {item.why} Cash: {plan.cash_note}"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ticket", type=int, help="work only this ticket (no reset)")
    ap.add_argument("--no-reset", action="store_true", help="full run without resetting the working DB")
    args = ap.parse_args()
    asyncio.run(main(args.ticket, reset=args.ticket is None and not args.no_reset))
