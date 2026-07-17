---
name: joule-capability-generator
description: >-
  Generates a complete SAP Joule capability package — all YAML files, folder
  structure, and deployment config — for connecting Joule to an A2A-compatible
  agent running on SAP Application Foundation (BTP). Use this skill whenever
  the user wants to expose an agent to Joule, create or update a Joule
  capability, write a capability.sapdas.yaml, define Joule scenarios, wire up
  an agent-request function, create a da.sapdas.yaml, or package a .daar file
  for deployment. Trigger even if they just say "Joule" or "make my agent work
  in Joule" or "add Joule support" — this skill covers the full authoring
  workflow including the subagent (joule-capability-developer) that knows the
  guidelines in depth.
---

# Joule Capability Generator

This skill produces a complete, deployable Joule capability package for an A2A
agent hosted on SAP BTP. It covers the full authoring loop: gathering intent,
generating all required files, validating against the schema constraints, and
packaging into a `.daar` archive ready for deployment.

## When to trigger

Use this skill whenever the user:
- Wants to expose an existing agent to SAP Joule
- Asks about `capability.sapdas.yaml`, `da.sapdas.yaml`, or Joule scenarios
- Mentions "Joule capability", "Joule skill", or "trigger my agent from Joule"
- Needs to update or add scenarios to an existing capability
- Wants to package or redeploy a Joule `.daar` file
- Asks **how to render** a specific output type in Joule (list, card, quick replies, etc.)
- Asks how to parse a JSON response from their agent and display it in Joule
- Wants a sample Joule function script for any rendering pattern

## Mode: answering rendering questions

If the user is asking a **"how do I render X"** question rather than requesting a full capability package, skip Steps 1–5 and go straight to producing the relevant function YAML snippet with a brief explanation. Always:
1. Show the exact `agent_call.yaml` (or relevant function snippet) with SpEL expressions filled in
2. State the **agent contract** — what JSON shape the agent must return for the script to work
3. Explain any non-obvious SpEL (e.g., `.toJson()`, `.![fieldName]` projection)

For composite layouts (multiple UI elements in one response — e.g., list card + quick replies), see `references/output-type-templates.md` — the **Composite layouts** section has ready-to-use patterns.

## Step 1 — Gather inputs

Ask (or infer from context) the following. The first four are required; the rest
have sensible defaults.

| # | Field | Example |
|---|-------|---------|
| 1 | **Agent name** (human-readable) | `Requisition Agent` |
| 2 | **Destination name** (SAP BTP destination, UPPER_SNAKE_CASE, **unique per agent**) | `ORCHESTRATOR_REQUISITION_AGENT` |
| 3 | **Namespace** (`com.<org>.<domain>.<subdomain>`) | `com.sap.appfnd.procode.procurement` |
| 4 | **Scenarios** — for each: title (≤32 chars), 2-4 sentence description (≤1000 chars), and whether it involves write operations needing user confirmation | See examples below |
| 5 | **Output type** per scenario (optional) — `genai` \| `text` \| `card` \| `list` \| `quick_replies` | Default: `genai` for A2A agents |
| 6 | **Capability name** (alphanumeric + underscore, ≤50 chars) | `orchestrator_requisition_agent` |
| 7 | **Version** | `1.0.0` |
| 8 | **Output folder** | `./joule-capability` |

**Important:** the destination name must be unique for each agent. If the user
already has a BTP destination configured for their agent, use that exact string.

### Output types — when to use which

Output type controls how Joule renders the agent's response. Each scenario can
have its own output type; if all scenarios share one type, a single
`agent_call.yaml` is generated. If scenarios have mixed types, named function
files are generated per type (e.g., `tools/agent_call_card.yaml`).

| Type | When to use | What changes |
|------|-------------|--------------|
| **`genai`** *(default for A2A)* | Conversational agents that return free-form text; Joule's AI rewrites the response | Scenario keeps `response_context`; function returns `agent_result` for GenAI rendering |
| **`text`** | Agent returns a plain string you want shown verbatim — no AI rewrite | Scenario drops `response_context`; function emits a `message` action with `type: text` |
| **`card`** | Agent returns structured data to display as a titled card with fields | Scenario drops `response_context`; function emits a `message` action with `type: card`; agent must return JSON with `title`, `subtitle`, `description`, `status` fields |
| **`list`** | Agent returns a collection of items (e.g., search results, PR list) | Scenario drops `response_context`; function emits a `message` action with `type: list`; agent must return JSON with an `items` array |
| **`quick_replies`** | Agent asks a follow-up question and provides options for the user to tap | Scenario drops `response_context`; `input-required` branch emits suggestion chips alongside the question text |

If the user hasn't specified an output type and the capability is for an A2A
agent, default to **`genai`** — it's the most forgiving and works with any
agent response format.

### Good scenario descriptions

Descriptions are how Joule routes user intent — they must be specific about
what the scenario *does*, written in plain English, 2-4 sentences, max 1000
chars. They should NOT:
- Mention other capabilities or features
- Use generic trigger words like "delete", "remove", "erase"
- Mention roles or personas (use `visibility_condition` for that)

**Example — create flow:**
> Guide the user through a 5-step conversational flow to create a new purchase
> requisition (PR) in SAP S/4HANA. Handles natural language intent capture
> (item, quantity, delivery requirement), product catalog search, unit-of-measure
> and delivery-date collection, policy compliance check (with justification if
> warnings arise), and final PR submission.

**Example — read-only lookup:**
> Look up the current status, approval workflow step, and associated purchase
> order number for one or more existing purchase requisitions in SAP S/4HANA.
> Delegates read-only queries and returns a plain-language status summary.

## Step 2 — Determine function files needed

Before generating, map each scenario's output type to a function file:

- All scenarios use `genai` (or no type specified) → single `tools/agent_call.yaml`
- One or more scenarios use a non-`genai` type → generate one function file per
  distinct type, named `tools/agent_call_<type>.yaml` (e.g., `tools/agent_call_card.yaml`)
- Each scenario's `target.name` must point to the correct function file

See `references/output-type-templates.md` for the exact function YAML per type.

## Step 3 — Generate the file tree

Produce the following structure under the output folder:

```
<output-folder>/
├── da.sapdas.yaml                            ← root DA config
└── a2a/
    ├── capability.sapdas.yaml                ← capability metadata & system alias
    ├── capability_context.yaml               ← shared context variable
    ├── scenarios/
    │   └── <scenario-name>.yaml              ← one file per scenario
    └── functions/
        └── tools/
            ├── agent_call.yaml               ← default (genai / A2A)
            ├── agent_call_text.yaml          ← only if a text-type scenario exists
            ├── agent_call_card.yaml          ← only if a card-type scenario exists
            ├── agent_call_list.yaml          ← only if a list-type scenario exists
            └── agent_call_quick_replies.yaml ← only if a quick_replies scenario exists
```

Only generate the function files that are actually needed.

See `references/file-templates.md` for capability/scenario/context templates and
`references/output-type-templates.md` for per-type function YAML.

## Step 3 — Validate before writing

Check every file against these hard limits **before** writing to disk:

| Constraint | Limit |
|-----------|-------|
| `metadata.name` | ≤50 chars, alphanumeric + underscore only |
| `metadata.namespace` | ≤100 chars, alphanumeric + dots only |
| `metadata.display_name` | ≤128 chars |
| `metadata.description` | ≤512 chars |
| `metadata.version` | ≤20 chars |
| Scenario `title` | ≤32 chars |
| Scenario `description` | ≤1000 chars |
| Context variable name | ≤64 chars, alphanumeric + hyphens |
| Schema version (`capability.sapdas.yaml`) | `3.27.0` |
| Schema version (`da.sapdas.yaml`) | `1.4.0` |
| Max scenarios | 200 |
| Max functions | 500 |
| Max function file size | 50 KB |

## Step 4 — Write all files

Write every file from the templates in `references/file-templates.md`,
substituting the user's values. Write the files in this order:
1. `da.sapdas.yaml`
2. `a2a/capability.sapdas.yaml`
3. `a2a/capability_context.yaml`
4. `a2a/scenarios/<name>.yaml` (one per scenario)
5. `a2a/functions/tools/agent_call.yaml`

## Step 5 — Summarise and next steps

After writing, tell the user:
1. What was generated (file tree)
2. How to package: `zip -r capability.daar <output-folder>/` (rename extension)
3. Where to deploy: SAP BTP Joule configuration → upload `.daar`
4. That the **destination name** they provided must match a real BTP destination
   pointing to their agent's A2A endpoint

If the user has write-operation scenarios (approve, submit, delete), remind them
that the `agent_call.yaml` already handles response states — their agent is
responsible for surfacing a confirmation prompt back through the A2A response.

## Using the joule-capability-developer subagent

For non-trivial requests, delegate to the **joule-capability-developer** subagent rather than generating files inline. Use the subagent when any of these apply:
- Mixed output types across scenarios (requires multiple function files)
- `user-confirmation` action groups
- `visibility_condition` (ibn_targets / ias_attributes)
- `conversation_starter` definitions
- `async: true` api-request flows
- Localization (i18n) wiring
- `deployment_extension.yaml` for environment-specific config

**Subagent input (pass as structured JSON):**
```json
{
  "agent_name": "...",
  "destination_name": "...",
  "namespace": "...",
  "capability_name": "...",
  "version": "...",
  "output_folder": "...",
  "scenarios": [
    {"title": "...", "description": "...", "output_type": "genai|text|card|list|quick_replies"}
  ]
}
```

The subagent has the full Joule Development Guide loaded, reads `references/file-templates.md` and `references/output-type-templates.md` itself, writes all files to the output folder, and returns a file-tree summary.

For simple single-scenario genai capabilities, generate inline using Steps 3–4 without delegating.
