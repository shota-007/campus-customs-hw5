"""What defines one agent role: its prompt file, output type, and the MCP tools it may touch."""

from dataclasses import dataclass

from ..config import PROMPTS_DIR
from ..models import AgentReport, Role


@dataclass(frozen=True)
class RoleSpec:
    role: Role
    title: str
    prompt_file: str
    output_type: type[AgentReport]
    mcp_tools: frozenset[str]

    @property
    def prompt(self) -> str:
        return (PROMPTS_DIR / self.prompt_file).read_text(encoding="utf-8")
