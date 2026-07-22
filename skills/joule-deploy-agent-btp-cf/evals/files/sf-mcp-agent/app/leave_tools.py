"""Tool stubs that defer to MCP / Agent Gateway for SuccessFactors."""
import json


def get_employee_profile(user_id: str) -> str:
    return json.dumps({
        "message": "Use MCP tools to get actual data.",
        "tool": "get_employee_profile",
        "system": "SuccessFactors",
        "user_id": user_id,
    })


def get_leave_balance(user_id: str) -> str:
    return json.dumps({
        "message": "Use MCP tools to get actual data.",
        "tool": "get_leave_balance",
        "system": "SuccessFactors",
        "user_id": user_id,
    })
