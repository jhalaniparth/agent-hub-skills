# Deploy plan — leave-agent (BTP CF dry run)

## Agent type
A2A agent (`A2AStarletteApplication` + uvicorn). Reads `PORT` from the environment. Health endpoint: `/.well-known/agent.json`.

## Backends discovered from code
- **SuccessFactors** — `app/sf_client.py` reads `SF_BASE_URL`, `SF_USERNAME`, `SF_PASSWORD` and calls SF OData (`/odata/v2/User`).
- **AI Core** — `sap-ai-sdk-gen` is in `requirements.txt` (LLM); credential loader from the skill loads the shared `AICORE` destination.

Per the deploy-agent-btp-cf skill (`references/vcap-bridge.md`), the credential loader also wires **S/4HANA** via a destination named `S4HANA` into `S4_BASE_URL` / `S4_USERNAME` / `S4_PASSWORD`.

## Destinations to create (skill names — shared subaccount)

| Destination name | Auth | Purpose | Env vars populated |
|---|---|---|---|
| `S4HANA` | BasicAuthentication | S/4HANA OData (skill-mandated) | `S4_BASE_URL`, `S4_USERNAME`, `S4_PASSWORD` |
| `AICORE` | (additional properties `aicore_*`) | Shared AI Core | `AICORE_AUTH_URL`, `AICORE_CLIENT_ID`, `AICORE_CLIENT_SECRET`, `AICORE_BASE_URL`, `AICORE_RESOURCE_GROUP` |

Unique naming: the skill hardcodes destination names `S4HANA` and `AICORE` (no per-agent rename). In a shared subaccount these global names are used as-is.

## CF service binding
- Destination service instance: `jouleagent-dest` (`destination` / `lite`)
- Bound via `manifest.yml` → `services: [jouleagent-dest]`

## Deployment files prepared
- `Procfile`, `runtime.txt` (python-3.11.x), `manifest.yml` (app name `leave-agent`)
- Credential-loading block inserted at top of `app/main.py` (see `outputs/main_credential_loader.py`)

## Dry-run constraints (not executed)
- Did **not** run `cf push`
- Did **not** call Destination Service APIs
- Did **not** request live passwords

## Questions for the user (before a real push)
1. Confirm the shared subaccount already has (or can create) destinations named exactly `S4HANA` and `AICORE`.
2. Provide S/4HANA Basic Auth URL, username, and password for the `S4HANA` destination (skill expects this destination).
3. Confirm AI Core additional properties on `AICORE` (`aicore_auth_url`, `aicore_client_id`, `aicore_client_secret`, `aicore_base_url`, `aicore_resource_group`) — or plan to set the five `AICORE_*` env vars via `cf set-env` instead.
4. Confirm region / CF org+space and whether `jouleagent-dest` already exists.
5. After push, confirm the public route so we can set `AGENT_PUBLIC_URL` and restage.
