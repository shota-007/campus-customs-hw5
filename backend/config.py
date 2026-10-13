"""Settings shared by the whole backend: paths, the one model, and the safety limits."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
PROMPTS_DIR = BACKEND_DIR / "prompts"
OUTPUT_DIR = ROOT / "output"
AUDIT_TRAIL_PATH = OUTPUT_DIR / "audit_trail.json"

ORIGINAL_DB = ROOT / "data" / "campus_customs.db"
WORKING_DB = ROOT / "data" / "campus_customs_new.db"
MCP_SERVER_SCRIPT = ROOT / "mcp_server" / "server.py"

# The project .env wins; the course-root .env (one level up) is the fallback.
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / ".env")

# ---- Model: every agent uses exactly this one, through Portkey ----
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"

# Portkey's gpt-6-luna deployment only allows function tools + reasoning on the
# Responses API (/v1/responses), so agents use OpenAIResponsesModel. Low reasoning
# effort and a per-response output cap keep each turn cheap.
MODEL_SETTINGS = OpenAIResponsesModelSettings(max_tokens=1800, openai_reasoning_effort="low")

# ---- Token / loop budget (one ticket = Boss + everyone it pulls in) ----
# All nested agent runs share one usage counter, so these are per-ticket totals.
TICKET_LIMITS = UsageLimits(request_limit=30, tool_calls_limit=45, total_tokens_limit=150_000)
TRIAGE_LIMITS = UsageLimits(request_limit=4, tool_calls_limit=4, total_tokens_limit=40_000)
MAX_DELEGATION_DEPTH = 2          # Boss -> specialist -> specialist, no deeper
MAX_DELEGATIONS_PER_TICKET = 8    # total hand-offs across the whole ticket
AUDIT_TEXT_LIMIT = 4000           # chars kept per prompt / tool result in the audit trail


def build_model() -> OpenAIResponsesModel:
    api_key = os.environ.get("PORTKEY_API_KEY")
    if not api_key:
        raise RuntimeError("PORTKEY_API_KEY is not set (expected in .env at the project or course root).")
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(base_url=PORTKEY_BASE_URL, api_key=api_key))
