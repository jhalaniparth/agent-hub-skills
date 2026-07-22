# Deploy plan — invoice-agent + gr-agent (DRY RUN)

Skill version: `skill-snapshot` (old/current). Destination names come from `references/vcap-bridge.md`.

## Discovery summary

| Project | Type | Backends | PORT | MCP migration |
|---------|------|----------|------|---------------|
| invoice-agent | A2A (`A2AStarletteApplication`) | S/4HANA (PO OData), AI Core | `os.environ.get("PORT", "8080")` — OK | N/A (direct `s4_client.py`) |
| gr-agent | A2A (`A2AStarletteApplication`) | S/4HANA (material doc OData), AI Core | `os.environ.get("PORT", "8080")` — OK | N/A (direct `s4_client.py`) |

Both already read `S4_BASE_URL` / `S4_USERNAME` / `S4_PASSWORD` from env in `s4_client.py`. Both list `sap-ai-sdk-gen` and `sap-cloud-sdk` in `requirements.txt`.

## Proposed destinations (skill-hardcoded names)

Shared Destination Service instance: `jouleagent-dest` (lite).

| Destination name | Used by | Auth | Notes |
|------------------|---------|------|-------|
| **S4HANA** | invoice-agent **and** gr-agent | BasicAuthentication | Hardcoded string in `_load_destinations()`. **Name collision** in a shared subaccount. |
| **AICORE** | invoice-agent **and** gr-agent | OAuth2ClientCredentials (aicore_* props) | Shared — intentional; same AI Core for both apps. |

Env vars populated after load (system-stable prefixes):

- S/4: `S4_BASE_URL`, `S4_USERNAME`, `S4_PASSWORD`
- AI Core: `AICORE_AUTH_URL`, `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET`, `AICORE_BASE_URL`, `AICORE_RESOURCE_GROUP`

## Collision implication (baseline behavior)

Because both loaders call `get_subaccount_destination("S4HANA", ...)`, only one BTP destination named `S4HANA` can exist. Both agents receive the same URL/user/password. The old skill does **not** propose per-agent names (e.g. `S4HANA_INVOICE` / `S4HANA_GR`).

## CF files that would be created (not applied in dry run)

For each project directory (`invoice-agent/`, `gr-agent/`):

**Procfile**
```
web: python app/main.py --host 0.0.0.0 --port $PORT
```

**runtime.txt**
```
python-3.11.x
```

**manifest.yml** (names differ per app)
```yaml
---
applications:
  - name: invoice-agent   # or gr-agent
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

## Steps skipped in this dry run

- `cf create-service destination lite jouleagent-dest`
- Real Destination Service API / Cockpit destination creation with live passwords
- `cf push` / `cf set-env AGENT_PUBLIC_URL` / `cf restage`
- Live curl of `/.well-known/agent.json`

## Code edits that would be applied (documented only)

1. Insert full VCAP bridge + `_load_destinations()` from `vcap-bridge.md` at the top of each `app/main.py` (see `invoice_agent_loader.py` / `gr_agent_loader.py`).
2. Ensure `set_aicore_config()` (if added later) runs **after** `_load_destinations()`.
3. Leave `s4_client.py` env-based auth as-is.

## Questions for the user (would ask before a real deploy)

1. Confirm a single shared `S4HANA` destination is acceptable for both agents, or whether they need different S/4 systems/credentials (old skill cannot express unique names).
2. Confirm `AICORE` destination properties are already exported in BTP (`aicore_auth_url`, etc.).
3. Confirm CF org/space and whether `jouleagent-dest` already exists.
4. Preferred CF app names / routes for invoice-agent and gr-agent.
