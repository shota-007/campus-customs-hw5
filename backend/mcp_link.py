"""The team's only door to shop data: the Campus Customs MCP server over stdio.

There is no second shop-tools layer. Agents see MCP tools, filtered per role.
Before each call reaches the server, two guards run:
  * the `agent` argument is overwritten with the real caller's role, so an
    agent cannot act or sign in another agent's name;
  * human-only tools (approve_payment, reject_payment) are refused even if a
    filter mistake ever exposed them.
"""

import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import RunContext
from pydantic_ai.mcp import MCPToolset

from .config import MCP_SERVER_SCRIPT, ROOT, WORKING_DB
from .models import TeamDeps

HUMAN_ONLY_TOOLS = frozenset({"approve_payment", "reject_payment"})


async def _guard_tool_call(ctx: RunContext[TeamDeps], call_tool, name: str, tool_args: dict):
    if name in HUMAN_ONLY_TOOLS:
        raise PermissionError(f"{name} is human-only; agents may only call request_payment.")
    if "agent" in tool_args:
        tool_args = {**tool_args, "agent": ctx.deps.agent}
    return await call_tool(name, tool_args)


def build_mcp_toolset() -> MCPToolset:
    transport = StdioTransport(
        command=sys.executable,
        args=[str(MCP_SERVER_SCRIPT)],
        env={"CAMPUS_CUSTOMS_DB": str(WORKING_DB), "FASTMCP_SHOW_SERVER_BANNER": "false"},
        cwd=str(ROOT),
    )
    return MCPToolset(
        Client(transport),
        id="campus-customs",
        process_tool_call=_guard_tool_call,
        # A refusal (not enough cash, vendor blocked, duplicate request) is a business
        # answer, not a crash: show it to the model as the tool result.
        tool_error_behavior="failed",
    )


def human_mcp_client() -> Client:
    """Plain MCP client for the human side (dashboard approvals in later problems)."""
    return Client(
        StdioTransport(
            command=sys.executable,
            args=[str(MCP_SERVER_SCRIPT)],
            env={"CAMPUS_CUSTOMS_DB": str(WORKING_DB), "FASTMCP_SHOW_SERVER_BANNER": "false"},
            cwd=str(ROOT),
        )
    )
