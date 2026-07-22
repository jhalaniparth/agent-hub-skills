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
