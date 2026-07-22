"""Leave tools — MCP stubs replaced with direct OData calls via s4_client."""
import json
import os

from s4_client import get_goods_receipts, get_purchase_order

_SYSTEM_TYPE = os.environ.get("S4_SYSTEM_TYPE", "PUBLIC_CLOUD")


async def get_employee_profile(user_id: str) -> str:
    """Fetch employee profile via direct OData (replaces MCP Agent Gateway stub)."""
    try:
        data = await get_purchase_order(user_id, _SYSTEM_TYPE)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "tool": "get_employee_profile"})
    if "error" in data:
        return json.dumps({"status": "not_found", "tool": "get_employee_profile", **data})
    return json.dumps({
        "status": "success",
        "tool": "get_employee_profile",
        "system_type": _SYSTEM_TYPE,
        "user_id": user_id,
        **data,
    })


async def get_leave_balance(user_id: str) -> str:
    """Fetch leave balance via direct OData (replaces MCP Agent Gateway stub)."""
    try:
        results = await get_goods_receipts(user_id, _SYSTEM_TYPE)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e), "tool": "get_leave_balance"})
    return json.dumps({
        "status": "success",
        "tool": "get_leave_balance",
        "system_type": _SYSTEM_TYPE,
        "user_id": user_id,
        "results": results,
    })
