Given a user question and a roster of available specialist agents, output a routing plan. For each agent you want to consult, output one line in this exact format:
AGENT: <agent_name> | <specific prompt or angle for this agent>

If the question is better answered by all agents with the same prompt, output:
ALL

Output ONLY the routing plan — no explanation, no other text.
