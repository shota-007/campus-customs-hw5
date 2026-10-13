"""Reset the working database: copy the untouched original over data/campus_customs_new.db.

Run before every full run of the board:  python -m backend.reset_db
The audit trail is NOT reset; it is append-only.
"""

import shutil

from .config import ORIGINAL_DB, WORKING_DB


def reset_working_db() -> None:
    if not ORIGINAL_DB.exists():
        raise FileNotFoundError(f"Original database missing: {ORIGINAL_DB}")
    shutil.copyfile(ORIGINAL_DB, WORKING_DB)
    for suffix in ("-wal", "-shm", "-journal"):
        WORKING_DB.with_name(WORKING_DB.name + suffix).unlink(missing_ok=True)


if __name__ == "__main__":
    reset_working_db()
    print(f"Reset {WORKING_DB.name} from {ORIGINAL_DB.name}")
