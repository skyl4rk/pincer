# agents.py — Dynamic subagent loader
#
# Scans agents/*/ for subagent definitions at startup.
# Each subdirectory must contain IDENTITY.MD and ROLE.MD.
# An optional agent.cfg controls the model and enabled flag.
#
# agent.cfg format (key=value, one per line, # comments supported):
#   model=google/gemini-2.0-flash-001
#   enabled=true
#
# Usage:
#   from agents import load_agents
#   agents = load_agents()   # returns list of Agent dataclass instances
#
# Adding a new subagent requires only creating a new directory under agents/.
# No code changes needed.

from dataclasses import dataclass
from pathlib import Path

import config

PROJECT_DIR = Path(__file__).parent
AGENTS_DIR  = PROJECT_DIR / "agents"


@dataclass
class Agent:
    """Represents one subagent loaded from an agents/*/ directory."""
    name:     str     # directory name, used as the agent's identifier
    identity: str     # content of IDENTITY.MD (persona / system prompt)
    role:     str     # content of ROLE.MD (role description)
    model:    str     # OpenRouter model ID
    enabled:  bool    # whether this agent is active
    path:     Path    # path to the agent directory


def load_agents() -> list:
    """
    Scan agents/*/ and return a list of enabled Agent objects.

    Discovery rules:
      - Each immediate subdirectory of agents/ is a candidate.
      - Must contain both IDENTITY.MD and ROLE.MD.
      - If agent.cfg is missing, defaults to the main model and enabled=true.
      - Disabled agents (enabled=false in agent.cfg) are excluded from the list.
    """
    if not AGENTS_DIR.exists():
        return []

    agents = []
    for agent_dir in sorted(AGENTS_DIR.iterdir()):
        if not agent_dir.is_dir():
            continue

        identity_path = agent_dir / "IDENTITY.MD"
        role_path     = agent_dir / "ROLE.MD"

        if not identity_path.exists() or not role_path.exists():
            continue

        identity = identity_path.read_text().strip()
        role     = role_path.read_text().strip()

        # Defaults
        model   = config.OPENROUTER_MODEL
        enabled = True

        cfg_path = agent_dir / "agent.cfg"
        if cfg_path.exists():
            for line in cfg_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip().lower()
                val = val.strip()
                if key == "model" and val:
                    model = val
                elif key == "enabled":
                    enabled = val.lower() in ("true", "1", "yes")

        if not enabled:
            continue

        agents.append(Agent(
            name     = agent_dir.name,
            identity = identity,
            role     = role,
            model    = model,
            enabled  = enabled,
            path     = agent_dir,
        ))

    return agents


def format_roster(agents: list) -> str:
    """Return a human-readable roster string for listing available subagents."""
    if not agents:
        return "No subagents defined. Add directories to agents/ to create subagents."
    lines = [f"Subagents ({len(agents)} loaded):"]
    for a in agents:
        lines.append(f"  • {a.name}  [{a.model}]")
        # Show first line of role as a brief description
        first_role_line = a.role.splitlines()[0] if a.role else ""
        if first_role_line:
            lines.append(f"    {first_role_line}")
    return "\n".join(lines)
