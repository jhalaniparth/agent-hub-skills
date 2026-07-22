"""Goods Receipt Agent — S/4HANA material documents."""
import os
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from s4_client import get_goods_receipt  # noqa: F401


def create_app():
    return A2AStarletteApplication(agent_card={"name": "gr-agent", "url": os.environ.get("AGENT_PUBLIC_URL", "")})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("main:create_app", host="0.0.0.0", port=port, factory=True)
