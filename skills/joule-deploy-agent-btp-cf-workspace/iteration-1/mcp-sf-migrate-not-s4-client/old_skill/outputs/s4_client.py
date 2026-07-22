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
