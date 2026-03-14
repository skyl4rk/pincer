# orchestrator.py — Dynamic multi-agent orchestration
#
# The orchestrator dispatches questions to dynamically discovered subagents
# (defined in agents/*/). An orchestrator agent (defined in orchestrator_agent/)
# decides which subagents to invoke and with what prompts. A synthesis step
# combines all specialist outputs into a single final response.
#
# Called from agent.py via:
#   orchestrate: <question>   — intelligent routing through orchestrator LLM
#   ensemble: <question>      — shorthand alias (calls all agents, no routing)
#
# Subagents are discovered at call time so adding a new agent directory takes
# effect without restarting the agent.

import threading
import requests
from pathlib import Path

import config
import agents as _agents_mod

PROJECT_DIR        = Path(__file__).parent
ORCHESTRATOR_DIR   = PROJECT_DIR / "orchestrator_agent"

# Default orchestrator persona if orchestrator_agent/ directory is absent
_DEFAULT_ORCHESTRATOR_IDENTITY = (
    "You are an orchestrator for a multi-agent system. "
    "Your job is to decide which specialist subagents should answer a given question "
    "and what specific angle each agent should focus on. "
    "Be selective — do not always call all agents. Pick the ones most relevant to the question."
)

_DEFAULT_ORCHESTRATOR_ROLE = (
    "Given a user question and a roster of available specialist agents, output a routing plan. "
    "For each agent you want to consult, output one line in this exact format:\n"
    "AGENT: <agent_name> | <specific prompt or angle for this agent>\n\n"
    "If the question is better answered by all agents with the same prompt, output:\n"
    "ALL\n\n"
    "Output ONLY the routing plan — no explanation, no other text."
)

# Default synthesiser persona
_DEFAULT_SYNTHESISER_IDENTITY = (
    "You are a synthesis expert. You receive responses from multiple specialist agents "
    "who have each analysed the same question from a different angle. "
    "Integrate their insights into one clear, balanced, and useful response. "
    "Do not list each specialist separately — weave their contributions into a single "
    "coherent answer. Keep the final response concise."
)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def run(question: str, reply_fn) -> None:
    """
    Route a question through the orchestrator for intelligent agent selection,
    then synthesise the results.

    Steps:
      1. Load available subagents
      2. Ask the orchestrator LLM which agents to call and with what prompts
      3. Call selected agents in parallel
      4. Synthesise all outputs into a final response
    """
    available = _agents_mod.load_agents()
    if not available:
        reply_fn(
            "No subagents are defined. "
            "Add agent directories to agents/ and try again.\n"
            "Use 'create agent: <name>' to create a new subagent."
        )
        return

    reply_fn(f"Orchestrating across {len(available)} agent(s)…")

    # Step 1: Ask orchestrator to route the question
    routing = _plan_routing(question, available)

    # Step 2: Execute the routing plan
    if not routing:
        # Fallback: call all agents with the original question
        routing = {a.name: question for a in available}

    reply_fn(f"Consulting: {', '.join(routing.keys())}…")

    # Build a lookup map for quick access
    agent_map = {a.name: a for a in available}
    results   = {}
    errors    = []

    def call_agent(name: str, prompt: str) -> None:
        agent = agent_map.get(name)
        if not agent:
            errors.append(f"{name} (not found)")
            return
        system = f"{agent.identity}\n\n{agent.role}"
        response = _ask(agent.model, system, prompt)
        if response:
            results[name] = response
        else:
            errors.append(name)

    threads = [
        threading.Thread(target=call_agent, args=(name, prompt))
        for name, prompt in routing.items()
        if name in agent_map
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not results:
        reply_fn("All agent queries failed — check your API key and network connection.")
        return

    # Step 3: Synthesise
    synthesiser_system = _load_synthesiser_system()
    answers_block = "\n\n".join(
        f"[{name}]:\n{text}" for name, text in results.items()
    )
    synthesis_prompt = (
        f"Question: {question}\n\n"
        f"Specialist responses:\n\n{answers_block}\n\n"
        f"Synthesise these perspectives into one final response."
    )

    synthesis = _ask(config.OPENROUTER_MODEL, synthesiser_system, synthesis_prompt)

    if synthesis:
        reply_fn(synthesis)
    else:
        # Fallback: return raw specialist outputs if synthesis fails
        reply_fn("Synthesis failed. Specialist responses:\n\n" + answers_block)


def run_ensemble(question: str, reply_fn) -> None:
    """
    Call all available subagents in parallel with the same question (no routing).
    Used by the 'ensemble:' command as a simpler alternative to 'orchestrate:'.
    """
    available = _agents_mod.load_agents()
    if not available:
        reply_fn(
            "No subagents are defined. "
            "Add agent directories to agents/ to create subagents."
        )
        return

    names = ", ".join(a.name for a in available)
    reply_fn(f"Consulting all agents: {names}…")

    results = {}
    errors  = []

    def call_agent(agent: _agents_mod.Agent) -> None:
        system = f"{agent.identity}\n\n{agent.role}"
        response = _ask(agent.model, system, question)
        if response:
            results[agent.name] = response
        else:
            errors.append(agent.name)

    threads = [threading.Thread(target=call_agent, args=(a,)) for a in available]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not results:
        reply_fn("All agent queries failed — check your API key and network connection.")
        return

    synthesiser_system = _load_synthesiser_system()
    answers_block = "\n\n".join(
        f"[{name}]:\n{text}" for name, text in results.items()
    )
    synthesis_prompt = (
        f"Question: {question}\n\n"
        f"Specialist responses:\n\n{answers_block}\n\n"
        f"Synthesise these perspectives into one final response."
    )

    synthesis = _ask(config.OPENROUTER_MODEL, synthesiser_system, synthesis_prompt)
    if synthesis:
        reply_fn(synthesis)
    else:
        reply_fn("Synthesis failed. Specialist responses:\n\n" + answers_block)


# ---------------------------------------------------------------------------
# Routing planner
# ---------------------------------------------------------------------------

def _plan_routing(question: str, available: list) -> dict:
    """
    Ask the orchestrator LLM which agents to call and with what prompts.
    Returns a dict of {agent_name: prompt_string}.
    Returns empty dict on failure (caller falls back to all agents).
    """
    orchestrator_system = _load_orchestrator_system()

    roster_lines = []
    for a in available:
        first_role_line = a.role.splitlines()[0] if a.role else a.name
        roster_lines.append(f"  {a.name}: {first_role_line}")
    roster = "\n".join(roster_lines)

    routing_prompt = (
        f"Available agents:\n{roster}\n\n"
        f"Question: {question}"
    )

    raw = _ask(config.OPENROUTER_MODEL, orchestrator_system, routing_prompt)
    if not raw:
        return {}

    return _parse_routing(raw.strip(), available, question)


def _parse_routing(raw: str, available: list, fallback_question: str) -> dict:
    """
    Parse the orchestrator's routing plan into a {name: prompt} dict.

    Supported formats:
      ALL                              → call all agents with the original question
      AGENT: name | prompt             → call named agent with specific prompt
      AGENT: name                      → call named agent with original question
    """
    agent_names = {a.name.lower(): a.name for a in available}
    routing     = {}
    upper       = raw.upper().strip()

    # "ALL" means call every available agent with the original question
    if upper == "ALL" or upper.startswith("ALL\n"):
        return {a.name: fallback_question for a in available}

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Match "AGENT: name | prompt" or "AGENT: name"
        if line.upper().startswith("AGENT:"):
            body = line[6:].strip()
            if "|" in body:
                name_part, prompt_part = body.split("|", 1)
                name   = name_part.strip().lower()
                prompt = prompt_part.strip() or fallback_question
            else:
                name   = body.strip().lower()
                prompt = fallback_question
            # Resolve to canonical name
            canonical = agent_names.get(name)
            if canonical:
                routing[canonical] = prompt

    return routing


# ---------------------------------------------------------------------------
# Persona loaders
# ---------------------------------------------------------------------------

def _load_orchestrator_system() -> str:
    """Build the orchestrator's system prompt from orchestrator_agent/ files."""
    identity_path = ORCHESTRATOR_DIR / "IDENTITY.MD"
    role_path     = ORCHESTRATOR_DIR / "ROLE.MD"

    identity = (
        identity_path.read_text().strip()
        if identity_path.exists()
        else _DEFAULT_ORCHESTRATOR_IDENTITY
    )
    role = (
        role_path.read_text().strip()
        if role_path.exists()
        else _DEFAULT_ORCHESTRATOR_ROLE
    )
    return f"{identity}\n\n{role}"


def _load_synthesiser_system() -> str:
    """
    Build the synthesiser's system prompt.
    Looks for orchestrator_agent/SYNTHESISER.MD; falls back to default.
    """
    synth_path = ORCHESTRATOR_DIR / "SYNTHESISER.MD"
    if synth_path.exists():
        return synth_path.read_text().strip()
    return _DEFAULT_SYNTHESISER_IDENTITY


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def _ask(model: str, system_prompt: str, user_message: str) -> str:
    """Call one model with a system prompt and user message. Returns reply text."""
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/pincer",
                "X-Title": "Pincer",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system",  "content": system_prompt},
                    {"role": "user",    "content": user_message},
                ],
                "transforms": ["middle-out"],
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[orchestrator] Error from {model}: {e}")
        return ""
