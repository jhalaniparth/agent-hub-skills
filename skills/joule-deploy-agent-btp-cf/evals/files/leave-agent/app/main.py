"""Leave Agent — SuccessFactors only (no S/4HANA)."""
import os
import uvicorn
from a2a.server.apps import A2AStarletteApplication

# Placeholder: credentials should load from BTP destinations at deploy time
from sf_client import get_employee  # noqa: F401


def create_app():
    # Minimal stub for layout detection
    return A2AStarletteApplication(agent_card={"name": "leave-agent", "url": os.environ.get("AGENT_PUBLIC_URL", "")})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("main:create_app", host="0.0.0.0", port=port, factory=True)
