"""S/4HANA OData client for goods-receipt agent."""
import os
import httpx


def _auth():
    return httpx.BasicAuth(os.environ["S4_USERNAME"], os.environ["S4_PASSWORD"])


def _base():
    return os.environ["S4_BASE_URL"].rstrip("/")


async def get_goods_receipt(material_doc: str) -> dict:
    async with httpx.AsyncClient(auth=_auth(), timeout=30.0, verify=False) as c:
        r = await c.get(
            f"{_base()}/sap/opu/odata/sap/API_MATERIAL_DOCUMENT_SRV/A_MaterialDocumentHeader('{material_doc}')",
            params={"$format": "json"},
        )
        r.raise_for_status()
        return r.json()
