# Baseline eval transcript — mcp-sf-migrate-not-s4-client (old skill)

## Skill followed
`skills/joule-deploy-agent-btp-cf-workspace/skill-snapshot/SKILL.md`
+ `references/mcp-to-odata-migration.md`
+ `references/vcap-bridge.md`

## Project inspected
`old_skill/workspace-project/` — A2A agent named `sf-mcp-agent`.

Signals that triggered Step 1b:
- `leave_tools.py` stubs with `"Use MCP tools to get actual data."` (system: SuccessFactors)
- `agent_executor.py` using `sap_cloud_sdk.agentgateway.create_client` / `get_mcp_tools(server="successfactors-leave")`
- `mcp>=1.0.0` in `requirements.txt`

## What the old skill instructed (and what I did)
The migration reference is **S/4-focused**: create `app/s4_client.py` with Purchase Order / Goods Receipt / Supplier Invoice OData helpers, rewrite stubs to call that client, strip Agent Gateway loading, load destination **S4HANA** into `S4_*` env vars.

I followed that guidance literally on this SuccessFactors leave agent:

1. **Created `app/s4_client.py`** — exact skill template (S/4 OData, `S4_USERNAME` / `S4_PASSWORD` / `S4_BASE_URL`, destination name `S4HANA`).
2. **Rewrote `leave_tools.py`** — `get_employee_profile` → `get_purchase_order`; `get_leave_balance` → `get_goods_receipts` (async direct calls instead of MCP stubs).
3. **Simplified `agent_executor.py`** — removed Agent Gateway / `get_mcp_tools` / `call_mcp_tool`; fixed stream executor without per-request MCP tools.
4. **Wired credential loading in `app/main.py`** — VCAP bridge + `_load_destinations()` for **S4HANA** and **AICORE** before other imports.
5. **Cleaned `requirements.txt`** — removed `mcp>=1.0.0`; kept `httpx` and `sap-cloud-sdk`.
6. **Created CF files** — `Procfile`, `runtime.txt`, `manifest.yml` (app `sf-mcp-agent`, service `jouleagent-dest`).

## DRY RUN constraints honored
- No `cf push`
- No `cf create-service`
- No live Destination Service / BTP API calls
- No password prompts

## Outputs saved
- `s4_client.py`
- `leave_tools.py`
- `agent_executor.py`
- `main.py` (full file with credential loader prepended)
- `main_credential_loader.py` (loader block alone)
- `deploy_plan.md` (destinations: **S4HANA**, **AICORE**)
- `requirements.txt`, `Procfile`, `runtime.txt`, `manifest.yml`
- `transcript.md` (this file)

## Destination names recorded
- Backend: `S4HANA` → `S4_BASE_URL`, `S4_USERNAME`, `S4_PASSWORD`
- Shared LLM: `AICORE` → `AICORE_*`
- CF destination service binding: `jouleagent-dest`
