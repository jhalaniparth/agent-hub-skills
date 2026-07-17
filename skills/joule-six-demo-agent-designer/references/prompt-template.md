# Enriched Prompt Template

Use this template for each agent in Step 5. Substitute values from the user's Q&A answers and EKX context. The output is always plain text — no JSON, no code fences in the final output shown to the user.

```
I want to create an agent. The agent should act as a [Agent Name] for [Company/Context].

[ROLE AND SCOPE]
The agent should [2–3 sentences describing what it does and for whom, written as
third-person description of desired behaviour].

[MULTI-TURN MEMORY]
The agent should retain across the entire conversation: [specific list — order IDs,
customer tier, decisions made, actions taken]. It should not reset until the user
explicitly starts a new session.

[OBSERVABILITY]
The agent should log every API call: name, input parameters, response status, latency.
It should log every business rule evaluation: rule name, input values, outcome.
It should log every decision: what was decided, what data drove it, timestamp.

[ERROR HANDLING]
When calling [API name, e.g. API_SALES_ORDER_SRV]: if it returns 503 — the agent should
retry once after 5s, then inform the user and halt. It should not proceed with downstream
steps until resolved.
When calling [next API or rule]: [specific fallback behaviour based on adviser's answers]
[Continue for each API/rule identified]

[WORKFLOW STATE]
The agent should track progress through these steps:
1. [Step name] — [what the agent does]
2. [Step name] — [what the agent does]
[...continue]
If the conversation is interrupted, the agent should resume from the last completed step
and confirm the resumption point with the user before acting.

[AUDIT TRAIL]
The agent should record for every action: the business rule applied, the data values that
triggered it (e.g. credit score: 720, priority tier: Gold), the decision made, and the
timestamp. The user should be able to request this log at any point in the conversation.

[CONFIGURABILITY]
The agent should expose the following as adjustable parameters the user can change at
runtime (with defaults):
- [parameter_name] (default: [value]) — [what it controls]
- [parameter_name] (default: [value]) — [what it controls]
```
