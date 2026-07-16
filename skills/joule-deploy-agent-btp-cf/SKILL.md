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

## Step 1b — Replace MCP backend calls with direct OData calls (if applicable)

Skip this step if the agent does not use MCP for backend calls.

When an agent routes S/4HANA (or other API) calls through an MCP server / Agent Gateway, those calls require a user token that isn't available on CF without a full Joule setup. The fix is to call the OData APIs directly using credentials already loaded from the BTP Destination Service.

### 1. Identify what APIs the MCP tools wrap

Read `system_router.py` (or equivalent) to find the OData API ORD IDs being used, e.g.:
- `CE_PURCHASEORDER_0001` / `API_PURCHASEORDER_PROCESS_SRV` — Purchase Orders
- `SSPOPENITMGOODSRECEIPT_0001` / `API_MATERIAL_DOCUMENT_SRV` — Goods Receipts
- `API_SUPPLIERINVOICE_PROCESS_SRV` — Supplier Invoice posting

Read `invoice_tools.py` (or wherever tools are defined) to find which functions are stubs that defer to MCP. They typically look like:
```python
return json.dumps({"message": "Use MCP tools to get actual data.", ...})
```

### 2. Create `app/s4_client.py` — direct async OData calls

Create a new file `app/s4_client.py`. Credentials come from env vars that `_load_destinations()` populates at startup (`S4_BASE_URL` is just the hostname — the OData paths are built in full below).

```python
"""Direct OData client for SAP S/4HANA — credentials loaded from env vars set by main.py."""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)
_TIMEOUT = httpx.Timeout(30.0)


def _auth() -> httpx.BasicAuth:
    u = os.environ.get("S4_USERNAME", "")
    p = os.environ.get("S4_PASSWORD", "")
    if not u or not p:
        raise RuntimeError("S4_USERNAME / S4_PASSWORD not set — check BTP Destination 'S4HANA'")
    return httpx.BasicAuth(u, p)


def _base() -> str:
    url = os.environ.get("S4_BASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("S4_BASE_URL not set — check BTP Destination 'S4HANA'")
    return url


def _headers() -> dict:
    return {"Accept": "application/json", "sap-client": os.environ.get("S4_CLIENT", "100")}


async def _csrf(client: httpx.AsyncClient, url: str) -> str:
    r = await client.get(url, headers={**_headers(), "x-csrf-token": "Fetch"})
    r.raise_for_status()
    return r.headers.get("x-csrf-token", "")


# --- Purchase Order -------------------------------------------------------
# Public Cloud: OData V4 — /sap/opu/odata4/sap/api_purchaseorder_2/...
# Private/OP:  OData V2 — /sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV

async def get_purchase_order(po_number: str, system_type: str) -> dict[str, Any]:
    base = _base()
    async with httpx.AsyncClient(auth=_auth(), timeout=_TIMEOUT, verify=False) as c:
        if system_type == "PUBLIC_CLOUD":
            r = await c.get(
                f"{base}/sap/opu/odata4/sap/api_purchaseorder_2/srvd_a2x/sap/purchaseorder/0001/PurchaseOrder('{po_number}')",
                headers=_headers(), params={"$expand": "to_PurchaseOrderItem"},
            )
        else:
            r = await c.get(
                f"{base}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{po_number}')",
                headers=_headers(), params={"$expand": "to_PurchaseOrderItem", "$format": "json"},
            )
    logger.info("PO %s → HTTP %d", po_number, r.status_code)
    if r.status_code == 404:
        return {"error": f"PO {po_number} not found", "status_code": 404}
    r.raise_for_status()
    data = r.json()
    return data.get("d", data)


# --- Goods Receipts -------------------------------------------------------
# Public Cloud: OData V4 — /sap/opu/odata4/sap/api_goodsmovement/...
# Private/OP:  OData V2 — /sap/opu/odata/sap/API_MATERIAL_DOCUMENT_SRV

async def get_goods_receipts(po_number: str, system_type: str) -> list[dict[str, Any]]:
    base = _base()
    async with httpx.AsyncClient(auth=_auth(), timeout=_TIMEOUT, verify=False) as c:
        if system_type == "PUBLIC_CLOUD":
            r = await c.get(
                f"{base}/sap/opu/odata4/sap/api_goodsmovement/srvd_a2x/sap/goodsmovemnt/0001/GoodsMovement",
                headers=_headers(),
                params={"$filter": f"PurchaseOrder eq '{po_number}' and GoodsMovementType eq '101'", "$top": "100"},
            )
        else:
            r = await c.get(
                f"{base}/sap/opu/odata/sap/API_MATERIAL_DOCUMENT_SRV/A_MaterialDocumentItem",
                headers=_headers(),
                params={"$filter": f"PurchaseOrder eq '{po_number}' and GoodsMovementType eq '101'", "$format": "json", "$top": "100"},
            )
    logger.info("GR PO %s → HTTP %d", po_number, r.status_code)
    r.raise_for_status()
    data = r.json()
    if "d" in data:
        return data["d"].get("results", [])
    return data.get("value", [])


# --- Supplier Invoice posting ---------------------------------------------
# All flavours: /sap/opu/odata/sap/API_SUPPLIERINVOICE_PROCESS_SRV
# On-Premise prefix: OP_API_SUPPLIERINVOICE_PROCESS_SRV

async def post_supplier_invoice(
    invoice_id: str, invoice_number: str, invoice_date: str,
    vendor_id: str, company_code: str, currency: str,
    total_amount: float, po_number: str,
    line_items: list[dict[str, Any]], system_type: str,
) -> dict[str, Any]:
    srv = "OP_API_SUPPLIERINVOICE_PROCESS_SRV" if system_type == "ON_PREMISE" else "API_SUPPLIERINVOICE_PROCESS_SRV"
    url = f"{_base()}/sap/opu/odata/sap/{srv}"
    fiscal_year = invoice_date[:4] if len(invoice_date) >= 4 else ""
    posting_date = f"{invoice_date[:4]}-{invoice_date[4:6]}-{invoice_date[6:8]}" if len(invoice_date) == 8 else invoice_date
    items = [
        {
            "SupplierInvoiceItem": str((i + 1) * 10).zfill(4),
            "PurchaseOrder": po_number,
            "PurchaseOrderItem": li.get("po_item_ref", "0010").zfill(4),
            "PurchaseOrderItemQty": str(li.get("quantity", 0)),
            "SupplierInvoiceItemAmount": str(li.get("line_amount", 0)),
            "TaxCode": li.get("tax_code", ""),
        }
        for i, li in enumerate(line_items)
    ]
    payload = {
        "FiscalYear": fiscal_year, "CompanyCode": company_code,
        "DocumentDate": posting_date, "PostingDate": posting_date,
        "SupplierInvoiceIDByInvcgParty": invoice_number,
        "InvoicingParty": vendor_id, "DocumentCurrency": currency,
        "InvoiceGrossAmount": str(total_amount),
        "to_SupplierInvoiceItemGLAcct": {"results": []},
        "to_SuplrInvcItemPurOrdRef": {"results": items},
    }
    async with httpx.AsyncClient(auth=_auth(), timeout=_TIMEOUT, verify=False) as c:
        csrf = await _csrf(c, f"{url}/A_SupplierInvoice?$top=1&$format=json")
        r = await c.post(
            f"{url}/A_SupplierInvoice",
            headers={**_headers(), "Content-Type": "application/json", "x-csrf-token": csrf},
            content=json.dumps(payload),
        )
    logger.info("Invoice %s post → HTTP %d", invoice_id, r.status_code)
    if r.status_code in (200, 201):
        doc = r.json().get("d", r.json())
        return {"status": "posted", "sap_document_number": doc.get("SupplierInvoice", "")}
    return {"status": "error", "status_code": r.status_code, "error": r.text[:500]}
```

Make sure `httpx` is in `requirements.txt` (it usually is already via `a2a-sdk`).

### 3. Replace stub tool functions with async direct calls

In the tool file (e.g. `invoice_tools.py`), replace each stub function with an `async def` that calls `s4_client`:

```python
from s4_client import get_purchase_order, get_goods_receipts, post_supplier_invoice

@tool
async def get_purchase_order_tool(po_number: str, company_code: str) -> str:
    system_type = _system_router.get_system_type(company_code)
    try:
        data = await get_purchase_order(po_number, system_type)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
    if "error" in data:
        return json.dumps({"status": "not_found", **data})
    return json.dumps({"status": "success", "system_type": system_type, **data})

@tool
async def get_goods_receipt_tool(po_number: str, company_code: str) -> str:
    system_type = _system_router.get_system_type(company_code)
    try:
        results = await get_goods_receipts(po_number, system_type)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})
    return json.dumps({"status": "success", "po_number": po_number, "results": results})

@tool
async def post_invoice_to_sap(invoice_json: str, match_result_json: str) -> str:
    # ... confidence / duplicate checks unchanged ...
    result = await post_supplier_invoice(
        invoice_id=invoice_id, invoice_number=invoice_number,
        invoice_date=inv.get("invoice_date", ""), vendor_id=inv.get("vendor_id", ""),
        company_code=company_code, currency=inv.get("currency", "USD"),
        total_amount=float(inv.get("total_amount", 0)),
        po_number=inv.get("po_reference", ""),
        line_items=inv.get("line_items", []),
        system_type=system_type,
    )
    # ... log and return result ...
```

Also ensure `parse_edi_invoice_tool` includes `line_items` in its returned JSON — the matching engine needs them and they are often missing from stub implementations:
```python
"line_items": [{"po_item_ref": li.po_item_ref, "quantity": li.quantity,
                "unit_price": li.unit_price, "unit_of_measure": li.unit_of_measure,
                "line_amount": li.line_amount} for li in invoice.line_items],
```

### 4. Simplify `agent_executor.py` — remove MCP tool loading

Delete everything related to Agent Gateway and user token extraction. The simplified executor just streams the agent:

```python
class AgentExecutor(A2AAgentExecutor):
    def __init__(self):
        self.agent = SampleAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.context_id)
        try:
            async for item in self.agent.stream(query, task.context_id):
                if item["require_user_input"]:
                    await updater.update_status(TaskState.input_required,
                        new_agent_text_message(item["content"], task.context_id, task.id), final=True)
                    break
                elif item["is_task_complete"]:
                    await updater.add_artifact([Part(root=TextPart(text=item["content"]))], name="agent_result")
                    await updater.complete()
                    break
                else:
                    await updater.update_status(TaskState.working,
                        new_agent_text_message(item["content"], task.context_id, task.id))
        except Exception as e:
            logger.exception("Agent execution error")
            raise ServerError(error=InternalError()) from e
```

Remove the import of `mcp_tools` from `agent_executor.py`.

### 5. Simplify `agent.py` — remove the tools parameter

The agent now always uses the fixed tool list; no tools are passed per-request:

```python
async def stream(self, query: str, context_id: str) -> AsyncGenerator[dict, None]:
    # tools= argument removed — AP_INVOICE_TOOLS always used
    graph = create_agent(self.llm, tools=AP_INVOICE_TOOLS, ...)
```

### 6. Delete MCP files and clean requirements

```bash
rm app/mcp_tools.py app/util.py   # or equivalent files
```

In `requirements.txt`, remove `mcp>=1.0.0` (and `sap-cloud-sdk` Agent Gateway extras if present). Keep `httpx`.

---

## Step 2 — Wire up credential loading in main.py

Open `app/main.py` and insert this block **as the very first lines**, before all other imports.
This ensures S/4HANA and AI Core credentials are loaded from BTP Destination Service before
any module captures them at import time.

### Why a VCAP bridge is required on CF

`sap-cloud-sdk` reads Destination Service credentials from **either**:
- Kubernetes secret mounts at `/etc/secrets/appfnd/destination/default/`
- Env vars with prefix `CLOUD_SDK_CFG_DESTINATION_DEFAULT_*`

On plain Cloud Foundry the binding lands in `VCAP_SERVICES` — which the SDK **never reads**.
The `_bridge_vcap_to_sdk()` function below populates those env vars from `VCAP_SERVICES`
before `create_client()` is called, bridging the gap automatically.

```python
# Load credentials from BTP Destination Service before any other import
import json as _json
import logging as _logging
import os as _os

_logger_boot = _logging.getLogger(__name__)


def _setenv_if_missing(key, value):
    if value and not _os.environ.get(key):
        _os.environ[key] = str(value)


def _bridge_vcap_to_sdk() -> None:
    """Populate CLOUD_SDK_CFG_DESTINATION_DEFAULT_* from VCAP_SERVICES when running on CF.

    sap-cloud-sdk reads credentials from K8s secret mounts or these env vars.
    On plain CF the binding lands in VCAP_SERVICES, so we bridge the gap here.
    Only runs when VCAP_SERVICES is present (i.e. on CF); no-ops locally.
    """
    vcap_raw = _os.environ.get("VCAP_SERVICES")
    if not vcap_raw:
        return
    try:
        vcap = _json.loads(vcap_raw)
    except Exception:
        return

    dest_creds = None
    for _svc_name, instances in vcap.items():
        if "destination" in _svc_name.lower():
            if instances:
                dest_creds = instances[0].get("credentials", {})
                break

    if not dest_creds:
        return

    mapping = {
        "clientid":     "CLIENTID",
        "clientsecret": "CLIENTSECRET",
        "url":          "URL",        # OAuth token endpoint base
        "uri":          "URI",        # Destination service REST base
        "identityzone": "IDENTITYZONE",
    }
    for vcap_key, sdk_suffix in mapping.items():
        value = dest_creds.get(vcap_key)
        if value:
            _setenv_if_missing(f"CLOUD_SDK_CFG_DESTINATION_DEFAULT_{sdk_suffix}", value)

    _logger_boot.info("Bridged VCAP_SERVICES destination binding → CLOUD_SDK_CFG_DESTINATION_DEFAULT_* env vars")


def _load_destinations() -> None:
    try:
        from sap_cloud_sdk.destination import AccessStrategy, create_client
        client = create_client()

        # S/4HANA — BasicAuthentication destination
        # AccessStrategy.PROVIDER_ONLY: single-tenant app running in its own subaccount.
        # The default (SUBSCRIBER_FIRST) requires a tenant subdomain and will fail here.
        try:
            dest = client.get_subaccount_destination("S4HANA", access_strategy=AccessStrategy.PROVIDER_ONLY)
            props = dest.properties or {}
            _setenv_if_missing("S4_BASE_URL", dest.url)
            _setenv_if_missing("S4_USERNAME", props.get("User") or props.get("user"))
            _setenv_if_missing("S4_PASSWORD", props.get("Password") or props.get("password"))
            _logger_boot.info("S4HANA credentials loaded from destination")
        except Exception as e:
            _logger_boot.warning("Could not load S4HANA destination: %s", e)

        # AI Core — additional properties use aicore_* naming (exact BTP export format)
        try:
            dest = client.get_subaccount_destination("AICORE", access_strategy=AccessStrategy.PROVIDER_ONLY)
            props = dest.properties or {}
            _setenv_if_missing("AICORE_AUTH_URL",       props.get("aicore_auth_url"))
            _setenv_if_missing("AICORE_CLIENT_ID",      props.get("aicore_client_id"))
            _setenv_if_missing("AICORE_CLIENT_SECRET",  props.get("aicore_client_secret"))
            _setenv_if_missing("AICORE_BASE_URL",       props.get("aicore_base_url") or dest.url)
            _setenv_if_missing("AICORE_RESOURCE_GROUP", props.get("aicore_resource_group"))
            _logger_boot.info("AICORE credentials loaded from destination")
        except Exception as e:
            _logger_boot.warning("Could not load AICORE destination: %s", e)

    except Exception as e:
        _logger_boot.warning("Destination service unavailable, using env vars: %s", e)


_bridge_vcap_to_sdk()
_load_destinations()
```

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

| Symptom | Cause | Fix |
|---------|-------|-----|
| `SapException - No credentials found in any source` | AI Core env vars missing | Set 5 AICORE_ vars via `cf set-env` and restage (see below) |
| `S4_CONNECTION_ERROR: HTTP 401` | Wrong S/4HANA credentials | Check `S4_USERNAME` / `S4_PASSWORD` env vars |
| App crashes at start | Wrong command in Procfile | Check path and module:variable reference |
| Health check never passes | App not binding to `$PORT` | Ensure `--port $PORT` in start command |
| 503 from CF router | Import error / missing dep | `cf logs <app> --recent` |
| Destination loader warns at startup | No Destination service bound or instance wrong | Check `jouleagent-dest` exists and is bound |
| `litellm.APIConnectionError` wrapping S4 error label | Agent maps all LLM errors to S4_CONNECTION_ERROR | Check CF logs — it's usually AI Core, not S/4HANA |
| `failed to load destination configuration … env var not found: CLOUD_SDK_CFG_DESTINATION_DEFAULT_CLIENTID` | SDK doesn't read `VCAP_SERVICES` — binding exists but SDK can't see it | Add `_bridge_vcap_to_sdk()` from Step 2 before `create_client()` |
| `tenant subdomain must be provided for subscriber access` | `get_subaccount_destination()` defaults to `SUBSCRIBER_FIRST` which requires a tenant | Pass `access_strategy=AccessStrategy.PROVIDER_ONLY` (single-tenant apps running in their own subaccount) |

### Set AI Core credentials directly (if AICORE destination not yet configured in BTP)

```bash
cf set-env <app-name> AICORE_AUTH_URL      "https://<subdomain>.authentication.<region>.hana.ondemand.com/oauth/token"
cf set-env <app-name> AICORE_CLIENT_ID     "sb-..."
cf set-env <app-name> AICORE_CLIENT_SECRET "..."
cf set-env <app-name> AICORE_BASE_URL      "https://api.ai.prod.<region>.aws.ml.hana.ondemand.com/v2"
cf set-env <app-name> AICORE_RESOURCE_GROUP "default"
cf restage <app-name>
```

Get values from BTP Cockpit → AI Core service instance → Service Keys.

---

## MCP transport swap

For MCP servers only (A2A agents skip this section).

Replace `stdio_server` with a Starlette app using `StreamableHTTPSessionManager`:

```python
import os
from mcp.server import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.fastmcp.server import StreamableHTTPASGIApp
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

app = Server('my-mcp-server')
# ... register @app.list_tools() and @app.call_tool() unchanged ...

session_manager = StreamableHTTPSessionManager(
    app=app, event_store=None, json_response=False, stateless=True
)

async def health(request):
    return JSONResponse({'status': 'ok'})

starlette_app = Starlette(
    routes=[
        Route('/health', health),
        Route('/mcp', endpoint=StreamableHTTPASGIApp(session_manager)),
    ],
    lifespan=lambda _: session_manager.run(),
)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    uvicorn.run(starlette_app, host='0.0.0.0', port=port)
```

Use `/health` as the health check endpoint in `manifest.yml`.
Add to `requirements.txt`: `starlette`, `uvicorn[standard]`, `sse-starlette`, `httpx-sse`.
`stateless=True` is required for multi-instance CF scaling.
