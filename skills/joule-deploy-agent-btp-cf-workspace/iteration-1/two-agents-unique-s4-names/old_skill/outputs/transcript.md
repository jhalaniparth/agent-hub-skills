# Baseline eval transcript — two-agents-unique-s4-names (old skill)

**Skill path:** `skills/joule-deploy-agent-btp-cf-workspace/skill-snapshot/`  
**Workspace:** `.../iteration-1/two-agents-unique-s4-names/old_skill/workspace-project/`  
**Mode:** DRY RUN (no `cf push`, no Destination API, no live passwords)

## Skill followed

Read `SKILL.md` and `references/vcap-bridge.md` (plus skim of troubleshooting / MCP refs). Old skill Step 2 loads destinations with **hardcoded** names `"S4HANA"` and `"AICORE"`.

## Step 1 — Project layout (both agents)

### invoice-agent

- Entry: `app/main.py` — A2A (`A2AStarletteApplication`), factory + uvicorn.
- PORT: `os.environ.get("PORT", "8080")` — compliant.
- Backend: `app/s4_client.py` → `API_PURCHASEORDER_PROCESS_SRV` via `S4_*` env vars.
- Deps: `a2a-sdk`, `uvicorn`, `httpx`, `sap-ai-sdk-gen`, `sap-cloud-sdk`.
- No MCP / Agent Gateway stubs → **skip Step 1b**.

### gr-agent

- Entry: `app/main.py` — A2A, same pattern.
- PORT: from env — compliant.
- Backend: `app/s4_client.py` → `API_MATERIAL_DOCUMENT_SRV` via `S4_*` env vars.
- Same dependency set; no MCP → **skip Step 1b**.

## Destination proposal (faithful to old skill)

| Agent | S/4 destination name | AI Core destination name |
|-------|----------------------|--------------------------|
| invoice-agent | `S4HANA` | `AICORE` |
| gr-agent | `S4HANA` | `AICORE` |

Both agents in the **same** subaccount therefore share one `S4HANA` destination entry. Baseline does **not** invent per-agent discriminators; that would diverge from skill-snapshot.

Loaders still map into stable env prefixes: `S4_BASE_URL`, `S4_USERNAME`, `S4_PASSWORD` (and AICORE_*).

## Step 2 — Credential loaders (documented, not patched into apps)

Wrote full `_bridge_vcap_to_sdk` + `_load_destinations` blocks as:

- `outputs/invoice_agent_loader.py`
- `outputs/gr_agent_loader.py`

Identical destination lookup strings per skill template.

## Steps 3–6 — CF deploy (dry-run only)

Documented Procfile / runtime.txt / manifest.yml shape and post-push `AGENT_PUBLIC_URL` in `deploy_plan.md`. Did **not** run:

- `cf service` / `cf create-service`
- `cf push` / `cf set-env` / `cf restage`
- Destination create API or password prompts

## Outputs written

- `destinations.json`
- `invoice_agent_loader.py`
- `gr_agent_loader.py`
- `deploy_plan.md`
- `transcript.md`

## Baseline takeaway

Old skill hardcodes `S4HANA` for every S/4-backed agent. Deploying invoice-agent and gr-agent together produces a **destination name collision** on `S4HANA` while correctly sharing `AICORE`.
