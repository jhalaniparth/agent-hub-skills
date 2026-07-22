"""Loads tools from Agent Gateway MCP for SuccessFactors."""
from sap_cloud_sdk.agentgateway import create_client

agw_client = create_client()


async def get_mcp_tools():
    return await agw_client.get_mcp_tools(server="successfactors-leave")


async def call_mcp_tool(name: str, args: dict):
    return await agw_client.call_mcp_tool(name=name, arguments=args)
