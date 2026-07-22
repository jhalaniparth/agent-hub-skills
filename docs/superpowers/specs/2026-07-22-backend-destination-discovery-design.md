# Backend Destination Discovery for BTP CF Deploy Skill

**Date:** 2026-07-22  
**Skill:** `joule-deploy-agent-btp-cf`  
**Status:** Approved for implementation planning

## Problem

The deploy skill always assumes an S/4HANA backend. It hardcodes destination name `S4HANA` in `references/vcap-bridge.md`, asks for S/4 credentials regardless of what the agent needs, and the MCP→OData migration path only produces `s4_client.py`.

Agents may depend on other backends (SuccessFactors, Ariba, Concur, custom HTTP). Deployments share a common BTP subaccount, so a single destination name like `S4HANA` collides across agents.

## Goals

1. Traverse agent code to discover required backend systems (not assume S/4).
2. Confirm discoveries with the user before creating anything.
3. Create per-agent unique backend destinations: `<AGENT_NAME>_<SYSTEM>` (e.g. `INVOICE_AGENT_S4`).
4. Keep shared `AICORE` destination unchanged (name, create behavior, env mapping).
5. Create destinations via Destination Service REST/CLI first; fall back to Cockpit instructions + export file.
6. Generate `_load_destinations()` from the confirmed set (env prefixes stay system-stable).
7. Generalize MCP→direct-API migration for all catalog systems, not S/4 only.

## Non-goals

- Renaming or per-agent duplication of `AICORE`.
- Changing Joule capability / agent-facing destination names (handled by `joule-capability-generator`).
- Inventing credentials; user always supplies URL/auth secrets.

## Approach

**System catalog + generated loader** (Approach 2).

A reference catalog defines known systems, detection signals, destination-name suffixes, env prefixes, and auth property maps. Discovery maps code → catalog entries; the skill generates a per-agent credential loader and creates unique destinations. `AICORE` remains a fixed shared entry outside the per-agent catalog.

---

## Design

### 1. Deploy flow — Step 1.5 Discover backends

Insert between project layout scan (Step 1) and credential wiring (Step 2):

1. Derive `AGENT_NAME` → `UPPER_SNAKE_CASE`, preferring `manifest.yml` `applications[0].name`, else project folder name. Confirm with user if unclear.
2. Scan codebase for catalog signals (env prefixes, `*_client.py`, host/URL patterns, OData paths, import hints).
3. Always include shared `AICORE` in the runtime loader (no rename, no per-agent create).
4. Present a confirmation checklist, e.g.  
   `Found: S4 (Basic), SuccessFactors (OAuth2). AICORE shared. Create INVOICE_AGENT_S4 + INVOICE_AGENT_SUCCESSFACTORS? Add/remove?`
5. After confirm:
   - Create backend destinations (REST/CLI → Cockpit fallback).
   - Generate `_load_destinations()` for the confirmed set.
   - Continue with existing CF files / `cf push` / `AGENT_PUBLIC_URL` steps.

### 2. Backend system catalog

New file: `references/backend-catalog.md`.

| System code | Dest suffix | Env prefix | Detection signals (examples) | Auth default |
|-------------|-------------|------------|------------------------------|--------------|
| `S4` | `_S4` | `S4_` | `s4_client.py`, `S4_*` env, `/sap/opu/odata`, `API_*_SRV` | Basic |
| `SUCCESSFACTORS` | `_SUCCESSFACTORS` | `SF_` | `sf_client.py`, `SF_*`, `successfactors` host | Infer / Basic |
| `ARIBA` | `_ARIBA` | `ARIBA_` | `ariba_client.py`, `ARIBA_*` | Infer / Basic |
| `CONCUR` | `_CONCUR` | `CONCUR_` | `concur_client.py`, `CONCUR_*` | Infer / Basic |
| `CUSTOM` | `_<NAME>` | `<NAME>_` | Unknown HTTP base URL / client with no catalog match | Infer / Basic |

**Rules:**

- Destination name = `<AGENT_NAME><suffix>` (e.g. `INVOICE_AGENT_S4`).
- Env prefix is **system-stable** (`S4_BASE_URL`), not based on destination name — app/client code does not rename when the destination is unique.
- `AICORE` is not a per-agent catalog backend; it stays a fixed shared destination in the loader.
- Unknown backends become `CUSTOM`; the confirmation checklist asks for a short system code.
- Auth type: infer from existing client/env usage (Basic vs OAuth2 Client Credentials); default Basic when unclear.

### 3. Destination creation

New file: `references/destination-create.md`.

For each confirmed backend destination (not `AICORE`):

1. Collect secrets/config from the user (URL, auth fields). Never invent credentials.
2. Try create via Destination Service REST using the bound Destination service instance (`jouleagent-dest` or equivalent) — token from service key / VCAP-style credentials, then POST destination config with unique name, auth type, and catalog properties.
3. On failure → write `destinations/<DEST_NAME>.json` and print BTP Cockpit steps (Connectivity → Destinations → New) using that exact name and fields.
4. Idempotent: if destination name already exists, skip create and warn (do not overwrite by default).
5. Verify: read back destination name before generating the loader; if missing after Cockpit fallback, pause until user confirms creation.

`AICORE`: verify/load only; never create or rename in this step.

### 4. Generated credential loader

Update `references/vcap-bridge.md` from a hardcoded S/4+AI Core paste to a **generation template**:

- Keep `_bridge_vcap_to_sdk()` unchanged.
- Generate `_load_destinations()` from the confirmed backend list:
  - Always load shared `AICORE` → existing `AICORE_*` mapping.
  - For each backend: `get_subaccount_destination("<AGENT>_<SYSTEM>", AccessStrategy.PROVIDER_ONLY)` and map properties → that system’s env prefix using catalog rules (Basic: User/Password/url; OAuth2: client id/secret/token URL/url as detected).
- Missing destination → warning log, not crash (local/dev via env vars still works).
- Rewrite hardcoded credentials in clients to `os.environ.get("<PREFIX>_...")`.

Skill Step 2 becomes “insert the generated loader,” not “paste the S4HANA block.”

### 5. MCP → direct API migration (all systems)

Generalize and rename `references/mcp-to-odata-migration.md` → `references/mcp-to-direct-api-migration.md`. Update `SKILL.md` references accordingly.

When Agent Gateway / MCP stubs are detected for any catalog system:

1. Map MCP/ORD/API signals → catalog system(s).
2. Create or extend `app/<system>_client.py` using that system’s env prefix.
3. Replace stub tools with direct HTTP/OData (or system-appropriate API) calls.
4. Error messages reference the unique destination name (`INVOICE_AGENT_S4`, not `S4HANA`).
5. Remove Agent Gateway / MCP backend deps from `requirements.txt` as today.

S/4 OData remains one pattern in the guide; SF/Ariba/Concur/CUSTOM get patterns keyed off the catalog.

### 6. Skill artifacts

| File | Change |
|------|--------|
| `SKILL.md` | New Step 1.5; Step 2 uses generated loader; description no longer S/4-only |
| `references/backend-catalog.md` | **New** — catalog, signals, env/auth maps |
| `references/destination-create.md` | **New** — REST create + Cockpit fallback + idempotency |
| `references/vcap-bridge.md` | Template + generation rules |
| `references/mcp-to-direct-api-migration.md` | **Rename** from `mcp-to-odata-migration.md`; generic MCP → direct API for all catalog systems |
| `references/troubleshooting.md` | Unique dest missing, create failures, shared-subaccount collisions |

### 7. Success criteria

- Deploying an agent that only needs SuccessFactors never asks for S/4.
- Two agents in one subaccount get distinct `*_S4` (or other system) destinations.
- `AICORE` remains one shared destination.
- Non-S/4 MCP agents migrate to direct clients without forcing an S4 client.
- Destination create prefers REST/CLI; Cockpit fallback still produces a deployable unique name.

### 8. Error handling

| Case | Behavior |
|------|----------|
| No backends detected | Checklist shows only `AICORE` (shared); user may add systems manually |
| User removes a detected system | Do not create that destination; do not load it |
| REST create fails | Write export JSON + Cockpit steps; pause for confirmation |
| Destination already exists | Skip + warn |
| Destination missing at runtime | Warning log; fall back to existing env vars |
| Auth type unclear | Default Basic; note in checklist for user override |

---

## Decisions log

| Topic | Decision |
|-------|----------|
| Unique naming | `<AGENT_NAME>_<SYSTEM>` (e.g. `INVOICE_AGENT_S4`) |
| AICORE | Shared; no rename; no create in this flow |
| Destination create | REST/CLI first, Cockpit fallback |
| Detection | Heuristic scan + user confirmation checklist |
| Auth | Infer from code; Basic default when unclear |
| Implementation approach | System catalog + generated loader |
| MCP migration | All catalog systems, not S/4-only |
