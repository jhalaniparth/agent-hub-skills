# Transcript — baseline (old skill) dry run: sf-only-no-s4

## Skill followed
`skills/joule-deploy-agent-btp-cf-workspace/skill-snapshot/` (OLD deploy-agent-btp-cf).
Read `SKILL.md` and `references/vcap-bridge.md`. Did not use live CF/BTP APIs or `cf push`.

## Step 1 — Project layout
- Path: `old_skill/workspace-project/`
- Entry: `app/main.py` — A2A agent (`A2AStarletteApplication`), binds `PORT` from env (default 8080).
- Backend client: `app/sf_client.py` — SuccessFactors OData only (`SF_BASE_URL`, `SF_USERNAME`, `SF_PASSWORD`).
- Dependencies: `a2a-sdk`, `uvicorn`, `httpx`, `sap-ai-sdk-gen`, `sap-cloud-sdk`.
- No `mcp_tools.py` / Agent Gateway / MCP backend stubs → skipped Step 1b (MCP→OData migration).
- No `asset.yaml`; default health path `/.well-known/agent.json` used in manifest.

## Backends discovered
1. **SuccessFactors** (from code) — required for leave-agent runtime.
2. **AI Core** (from `sap-ai-sdk-gen` + skill vcap-bridge) — shared `AICORE` destination.
3. **S/4HANA** — **not present in application code**, but the OLD skill’s credential-loading block always loads destination `"S4HANA"` into `S4_*` env vars. Followed the skill as written.

## Destination names proposed (faithful to OLD skill)
- `S4HANA` — hardcoded in `references/vcap-bridge.md` (not unique / not agent-prefixed).
- `AICORE` — hardcoded shared name (kept as-is; not renamed per agent).

No SuccessFactors / `LEAVE_AGENT_*SUCCESSFACTORS*` destination was introduced by the skill reference; the loader does not set `SF_*` from Destination Service.

## Step 2 — Credential loader
Inserted the full `_bridge_vcap_to_sdk()` + `_load_destinations()` block from `vcap-bridge.md` at the top of `app/main.py` (before other imports).
Saved the same block to `outputs/main_credential_loader.py`.

## Step 3 — CF files written (no push)
Created in workspace-project:
- `Procfile`
- `runtime.txt` (`python-3.11.x`)
- `manifest.yml` (name `leave-agent`, service `jouleagent-dest`)

## Steps 4–6 skipped (dry run)
- Did not run `cf service` / `cf create-service`
- Did not run `cf push` / `cf set-env` / `cf restage`
- Did not ask for live passwords

## Assumptions
- Shared subaccount uses the skill’s global destination names (`S4HANA`, `AICORE`).
- Destination service instance name remains `jouleagent-dest` as in the skill template.
- SF credentials would still need to be supplied somehow at runtime (`SF_*`); the OLD skill does not document loading them from a destination.
- Faithful baseline intentionally follows the S4HANA-hardcoded loader even though this fixture is SuccessFactors-only.

## Outputs written
- `outputs/main_credential_loader.py`
- `outputs/deploy_plan.md`
- `outputs/transcript.md`
- Copies of modified project files under `outputs/` (see below).
