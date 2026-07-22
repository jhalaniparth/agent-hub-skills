"""SuccessFactors OData client — credentials from env."""
from __future__ import annotations

import os
import httpx

_TIMEOUT = httpx.Timeout(30.0)


def _auth() -> httpx.BasicAuth:
    u = os.environ.get("SF_USERNAME", "")
    p = os.environ.get("SF_PASSWORD", "")
    if not u or not p:
        raise RuntimeError("SF_USERNAME / SF_PASSWORD not set")
    return httpx.BasicAuth(u, p)


def _base() -> str:
    url = os.environ.get("SF_BASE_URL", "").rstrip("/")
    if not url:
        raise RuntimeError("SF_BASE_URL not set")
    return url


async def get_employee(user_id: str) -> dict:
    base = _base()
    async with httpx.AsyncClient(auth=_auth(), timeout=_TIMEOUT) as c:
        r = await c.get(f"{base}/odata/v2/User('{user_id}')")
        r.raise_for_status()
        return r.json()
