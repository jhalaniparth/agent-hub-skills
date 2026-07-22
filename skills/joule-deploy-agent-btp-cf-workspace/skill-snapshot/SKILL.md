---
name: deploy-agent-btp-cf
description: >
  Deploy a Python A2A or MCP agent to SAP BTP Cloud Foundry. Use this skill whenever
  the user wants to push an agent to BTP CF, deploy to Cloud Foundry, create a manifest.yml
  for an agent, wire up SAP Destination Service credentials (AI Core, S/4HANA), or
  troubleshoot a CF-deployed agent that can't connect to AI Core or S/4HANA.
  Also triggers for: "cf push agent", "deploy to BTP", "push to Cloud Foundry",
  "agent not working on CF", "S4_CONNECTION_ERROR on CF", "No credentials found in any source",
  "replace MCP calls with direct OData", "agent uses MCP for S4 calls", "remove Agent Gateway".
---

# Deploy Python Agent to SAP BTP Cloud Foundry

This is an **execution skill** — follow each step by actually running the commands and
making the file edits. Do not just show the user what to do; do it.

Covers two agent types: **A2A agents** (using `a2a-sdk` + uvicorn) and **MCP servers**
(using `mcp` + streamable HTTP). Read the project first to identify which you have.

---

## Step 1 — Read the project layout

Use the Read and Bash tools to inspect:
- `app/main.py` (or `server.py`) — entry point, port binding, health endpoint
- `requirements.txt` — dependencies
- `asset.yaml` (if present) — health probe paths, port

Identify the agent type:
- **A2A agent**: has `from a2a.server.apps import A2AStarletteApplication` → already HTTP, continue
- **MCP server**: has `from mcp.server import Server` + `stdio_server` → needs transport swap first (see [MCP transport swap](#mcp-transport-swap) at the bottom)

Confirm the app reads `PORT` from `os.environ.get("PORT", ...)` — if it hardcodes a port, fix it now.

Also check whether the agent uses MCP for backend API calls (S/4HANA, etc.) — look for any of:
- `mcp_tools.py` or similar file that calls `agw_client.call_mcp_tool` / `get_mcp_tools`
- `agent_executor.py` loading tools from an Agent Gateway (`create_client` from `sap_cloud_sdk.agentgateway`)
- Tool functions that return stub messages like `"Use MCP tools to get actual data"`
- `mcp>=1.0.0` in `requirements.txt`

If any of these are present, follow **Step 1b** before continuing to Step 2.

---

## Step 1b — Replace MCP backend calls (if applicable)

Skip this step if the agent does not use MCP for backend calls.

Read `references/mcp-to-odata-migration.md` and follow it as a subagent task:
- Input: list of detected MCP files, agent type (PUBLIC_CLOUD / ON_PREMISE / PRIVATE_CLOUD)
- It will create app/s4_client.py, rewrite tool stubs, simplify agent_executor.py and agent.py, and clean requirements.txt
- It returns: a summary of all files modified/created

---

## Step 2 — Wire up credential loading in main.py

Open `app/main.py` and insert the full credential-loading block from `references/vcap-bridge.md`
as the very first lines, before all other imports. This ensures S/4HANA and AI Core credentials
are loaded from BTP Destination Service before any module captures them at import time.

On plain Cloud Foundry, `VCAP_SERVICES` holds the Destination Service binding but `sap-cloud-sdk`
only reads K8s secret mounts or `CLOUD_SDK_CFG_DESTINATION_DEFAULT_*` env vars. The `_bridge_vcap_to_sdk()`
function translates the VCAP binding into those env vars automatically — it no-ops locally.

Then ensure `set_aicore_config()` is called **after** `_load_destinations()` — not before.

If the project has a `s4_client.py` with hardcoded S4 credentials, replace them with
`os.environ.get(...)` reads so the destination-loaded values take effect.

---

## Step 3 — Create the three CF deployment files

Write these three files into the same directory as `requirements.txt`:

**Procfile** — adjust the module path to match the actual entry point:
```
web: python app/main.py --host 0.0.0.0 --port $PORT
```

**runtime.txt**:
```
python-3.11.x
```

**manifest.yml** — use the health endpoint from `asset.yaml` if present:
```yaml
---
applications:
  - name: <app-name>
    memory: 512M
    instances: 1
    buildpacks:
      - python_buildpack
    command: python app/main.py --host 0.0.0.0 --port $PORT
    health-check-type: http
    health-check-http-endpoint: /.well-known/agent.json
    services:
      - jouleagent-dest
    env:
      AGENT_PUBLIC_URL: ""
```

---

## Step 4 — Ensure the Destination service instance exists

Run `cf service jouleagent-dest` to check. If it is not found, create it:

```bash
cf create-service destination lite jouleagent-dest
```

Wait until `cf service jouleagent-dest` shows `create succeeded` before continuing.

---

## Step 5 — Run cf push

From the directory containing `manifest.yml`, run:

```bash
cf push
```

Watch for errors. Common ones:
- **Service not found**: the `jouleagent-dest` instance doesn't exist yet — go back to Step 4
- **Health check timeout**: app not binding to `$PORT` — check the Procfile command
- **503 / crash**: run `cf logs <app> --recent` to find the import error

---

## Step 6 — Set AGENT_PUBLIC_URL and verify

After a successful push, get the route from the cf push output, then:

```bash
cf set-env <app-name> AGENT_PUBLIC_URL "https://<app-name>.cfapps.<region>.hana.ondemand.com/"
cf restage <app-name>
```

Verify the agent card is reachable:
```bash
curl https://<app-name>.cfapps.<region>.hana.ondemand.com/.well-known/agent.json
```

---

## Troubleshooting

See `references/troubleshooting.md` for the full symptom/cause/fix table and AI Core credential setup commands.

Quick reference — most common causes:
- `No credentials found in any source` → AI Core env vars missing (see troubleshooting.md)
- `S4_CONNECTION_ERROR: HTTP 401` → Wrong S4_USERNAME / S4_PASSWORD
- Health check never passes → App not binding to $PORT in Procfile
- 503 from CF router → Run `cf logs <app> --recent` for import errors

---

## MCP transport swap

For MCP servers only (A2A agents skip this section).

Read `references/mcp-transport-swap.md` for the full Starlette + StreamableHTTPSessionManager pattern. Key points:
- Use `/health` as the health check endpoint in manifest.yml
- Add to requirements.txt: `starlette`, `uvicorn[standard]`, `sse-starlette`, `httpx-sse`
- `stateless=True` is required for multi-instance CF scaling
