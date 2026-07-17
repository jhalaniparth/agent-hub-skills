---
name: agent-hub-register
description: |
  Generates a valid agents.json registration entry for the SiX Agent Hub catalog.
  Use this skill whenever someone wants to register, add, or publish an agent to the
  Agent Hub — including phrases like "register my agent", "add this agent to the hub",
  "add to agents.json", "publish my agent", "onboard my agent to the catalog", or
  "how do I list my agent in the hub". The skill introspects the agent's codebase
  (README, manifest.yml, main.py, agent card, pyproject.toml) to auto-fill as many
  fields as possible and produces a complete JSON block ready to paste into agents.json.
  Always invoke this skill proactively when deployment to BTP CF has just completed
  and the user hasn't yet registered the agent.
---

# Agent Hub Registration

This skill reads the agent's codebase and generates a complete, schema-valid entry for
`data/agents.json` in the SiX Agent Hub repository. The goal is to do as much heavy
lifting as possible so the user only has to review and fill in the few fields that
genuinely require human judgment.

## When to Use

- User says "register my agent to the hub", "add to agents.json", "publish my agent",
  "onboard to Agent Hub", or similar
- Deployment just completed and the agent isn't in the catalog yet
- User wants to update an existing entry

## Steps

### Step 1 — Gather source material

Read these files from the current project directory (skip gracefully if absent):

- `README.md` — name, description, business process, tech stack
- `manifest.yml` — app name, memory, services (reveals deployment landscape)
- `app/main.py` or `main.py` — agent card endpoint (`/.well-known/agent.json`)
- `/.well-known/agent.json` or any `agent_card.py`/`agent_card.json` — structured metadata
- `pyproject.toml` or `requirements.txt` — tech stack components
- Any existing `agents.json` entry for this agent (check if `id` already exists)

Also note: the current git remote URL (`git remote get-url origin`) tells you the
`githubUrl`. The current git user email (`git config user.email`) is a starting point
for `owner`.

### Step 2 — Derive auto-fillable fields

Map what you found to the schema. Use the table below as a guide:

| Field | Where to derive it |
|---|---|
| `id` | Kebab-case of app name from `manifest.yml` or directory name. Must match `^[a-z0-9-]+$`. |
| `name` | README H1 title, or `name:` in manifest.yml, title-cased |
| `shortDescription` | First sentence of README description, trimmed to ≤160 chars |
| `agentType` | Use this precedence: (1) **`"joule"`** — README/code explicitly says the agent is exposed *as* a Joule capability or skill, or a `.daar` package is present. Binding `jouleagent-dest` alone means Joule *calls* the agent over HTTP — that is NOT sufficient on its own to set `"joule"`; it indicates connectivity, not type. (2) **`"workflow"`** — agent uses LangGraph, multi-step orchestration, or coordinates sub-agents. (3) **`"api-based"`** — FastAPI/Flask REST service with no LangGraph and no Joule capability registration. (4) **`"custom-ui"`** — has a dedicated front-end. When ambiguous, leave a note explaining what you detected and ask the user to confirm. |
| `techStack` | Parse `requirements.txt` / `pyproject.toml` for key packages. Map: `langgraph` → `LangGraph`, `litellm` → `LiteLLM`, `fastapi` → `FastAPI`, `httpx` → `httpx`, `sap-cloud-sdk` → `SAP Cloud SDK`. Always include `SAP BTP Cloud Foundry` if `manifest.yml` present. |
| `owner` | Git user email → format as `"Firstname Lastname <email> (SiX CIT Team)"`. Ask user to confirm. |
| `landscapes` | Derive from CF space/org in manifest or README. Default tier to `"DEV"`, status to `"unknown"`. Leave `accessUrl` as `"https://TODO"` if not found. |
| `githubUrl` | From `git remote get-url origin` |
| `isEndToEnd` | True if README mentions "end-to-end" or agent orchestrates multiple sub-agents |
| `autonomousDomain` | Infer from business process (Finance → "Autonomous Finance", Procurement → "Autonomous Procurement", etc.) |
| `source` | `"github"` if githubUrl is present, else `"manual"` |
| `createdAt` / `updatedAt` | Today's date (ISO format: YYYY-MM-DD) |

### Step 3 — Flag fields that need human judgment

Set these as `"TODO: ..."` placeholders with clear prompts:

```json
"industry": ["TODO: e.g. Manufacturing, Retail, Professional Services"],
"businessProcess": "TODO: e.g. Procure-to-Pay, Order-to-Cash, Record-to-Report",
"samplePrompts": [
  { "text": "TODO: Basic prompt — what would a new user ask?", "category": "Basic" },
  { "text": "TODO: Basic prompt — another everyday use case", "category": "Basic" },
  { "text": "TODO: Advanced prompt — multi-step or conditional task", "category": "Advanced" },
  { "text": "TODO: Edge case — unusual input, error scenario, or boundary condition", "category": "Edge Case" }
],
"landscapes": [
  {
    "systemId": "TODO: e.g. S4H-100",
    "tier": "DEV",
    "accessUrl": "TODO: https://your-app.cfapps.eu10.hana.ondemand.com",
    "status": "unknown",
    "region": "TODO: e.g. EU10",
    "requiredRoles": ["TODO: SAP role name if access-controlled, or remove this field"]
  }
]
```

If you can derive a confident value for any of these from the source material, fill it in
and note your confidence level in the summary. Don't leave a TODO where you're confident.

### Step 4 — Output the JSON block

Print the complete entry as a JSON object, formatted and ready to paste. Wrap it in a
markdown code block with the label `json`. Include ALL fields — both auto-filled and
TODO placeholders — so the user can see the full shape at once.

Then print a **"What to review"** checklist with one line per TODO, e.g.:
- `industry` — which SAP industry verticals does this agent serve?
- `businessProcess` — which end-to-end process? (Procure-to-Pay, Record-to-Report, etc.)
- `samplePrompts` — write 2 Basic, 1 Advanced, 1 Edge Case prompt from the user's perspective
- `landscapes.systemId` — the system identifier (found in BTP cockpit → Cloud Foundry)
- `landscapes.accessUrl` — the deployed app URL (from `cf app <name>` output)
- `owner` — confirm the name/email is correct

### Step 5 — Guide the merge

After the user fills in the TODOs, remind them:

> **Before submitting:**
> 1. Open `data/agents.json` in the Agent Hub repo
> 2. Add your entry to the `agents` array (alphabetical by `id` is preferred but not required)
> 3. Update `meta.totalAgents` (increment by 1)
> 4. Update `meta.lastUpdated` to today's date (YYYY-MM-DD)
> 5. Validate against the schema: `data/agents.schema.json`
> 6. Submit a pull request to `main`

If the user is in the Agent Hub repo directory, offer to do steps 2–4 automatically.

## Schema Reference

See `references/schema.md` for all allowed enum values, required fields, and the id format pattern.

## Integration

This skill is the final step of the **Create Demo-Ready Agents** workflow:
1. `joule-six-demo-agent-designer` — design intent
2. Joule Studio 2.0 — generate agent code
3. `deploy-agent-btp-cf` — deploy to BTP CF
4. `joule-capability-generator` — expose in Joule
5. **`agent-hub-register`** ← you are here

It can also be used standalone on any existing agent project.
