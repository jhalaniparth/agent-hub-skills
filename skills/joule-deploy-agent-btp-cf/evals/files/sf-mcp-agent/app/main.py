"""SF MCP Agent — backend calls go through Agent Gateway today."""
import os
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from leave_tools import get_employee_profile, get_leave_balance  # noqa: F401
from agent_executor import get_mcp_tools  # noqa: F401


def create_app():
    return A2AStarletteApplication(agent_card={"name": "sf-mcp-agent", "url": os.environ.get("AGENT_PUBLIC_URL", "")})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("main:create_app", host="0.0.0.0", port=port, factory=True)
