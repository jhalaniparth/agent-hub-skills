"""S/4HANA OData client for invoice agent."""
import os
import httpx


def _auth():
    return httpx.BasicAuth(os.environ["S4_USERNAME"], os.environ["S4_PASSWORD"])


def _base():
    return os.environ["S4_BASE_URL"].rstrip("/")


async def get_purchase_order(po_number: str) -> dict:
    async with httpx.AsyncClient(auth=_auth(), timeout=30.0, verify=False) as c:
        r = await c.get(
            f"{_base()}/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrder('{po_number}')",
            params={"$format": "json"},
        )
        r.raise_for_status()
        return r.json()
