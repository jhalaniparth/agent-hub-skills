# Deploy plan — sf-mcp-agent (DRY RUN)

## Agent type
A2A agent (`a2a-sdk` + uvicorn). Already HTTP; no MCP transport swap needed.

## MCP → direct OData migration (Step 1b)
Detected MCP / Agent Gateway usage:
- `leave_tools.py` stubs returning `"Use MCP tools to get actual data."`
- `agent_executor.py` calling `sap_cloud_sdk.agentgateway.create_client` / `get_mcp_tools`
- `mcp>=1.0.0` in `requirements.txt`

Per skill `references/mcp-to-odata-migration.md`:
1. Created `app/s4_client.py` with direct S/4HANA OData helpers (`get_purchase_order`, `get_goods_receipts`, `post_supplier_invoice`).
2. Rewrote `leave_tools.py` stubs as async functions calling `s4_client`.
3. Simplified `agent_executor.py` — removed Agent Gateway / MCP tool loading.
4. Removed `mcp>=1.0.0` from `requirements.txt`; kept `httpx`.

## Destinations to create (BTP subaccount)

| Destination name | Purpose | Auth | Env vars loaded |
|------------------|---------|------|-----------------|
| **S4HANA** | S/4HANA OData backend for direct API calls | BasicAuthentication | `S4_BASE_URL`, `S4_USERNAME`, `S4_PASSWORD` |
| **AICORE** | SAP AI Core LLM credentials | (additional properties) | `AICORE_AUTH_URL`, `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET`, `AICORE_BASE_URL`, `AICORE_RESOURCE_GROUP` |

Destination service instance: `jouleagent-dest` (lite plan), bound via `manifest.yml`.

## CF deployment files (created)
- `Procfile` — `python app/main.py --host 0.0.0.0 --port $PORT`
- `runtime.txt` — `python-3.11.x`
- `manifest.yml` — app name `sf-mcp-agent`, health `/.well-known/agent.json`, service `jouleagent-dest`

## Credential loading
Inserted VCAP → SDK bridge + `_load_destinations()` at the top of `app/main.py` (see `main_credential_loader.py` in outputs). Loads **S4HANA** then **AICORE** with `AccessStrategy.PROVIDER_ONLY`.

## DRY RUN — skipped
- `cf create-service destination lite jouleagent-dest`
- `cf push`
- `cf set-env` / `cf restage`
- Live Destination Service API calls / password prompts

## Questions for the user (before real push)
1. Confirm S/4HANA host URL, technical user, and password for destination **S4HANA**.
2. Confirm AI Core destination properties (`aicore_*`) for shared destination **AICORE**.
3. Confirm system type: `PUBLIC_CLOUD` vs `ON_PREMISE` / `PRIVATE_CLOUD` (controls OData V4 vs V2 paths).
4. Confirm CF org/space and whether `jouleagent-dest` already exists.
5. Desired public route / region for `AGENT_PUBLIC_URL`.
