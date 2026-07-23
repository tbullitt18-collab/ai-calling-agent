"""
MCP Client for MongoDB integration.
Connects to a MongoDB MCP server and exposes its tools.
"""

import os
import asyncio
from typing import List, Dict, Any

try:
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.session import ClientSession
except ImportError:
    # Fallback/mock if mcp is not available
    stdio_client = None


class MongoDBMCPClient:
    """Client for the MongoDB MCP Server."""
    
    def __init__(self, server_cmd: str = "npx", server_args: List[str] = ["-y", "@mongodb/mcp-server"]):
        self.server_cmd = server_cmd
        self.server_args = server_args
        self.session = None
        self._exit_stack = None
        self._connected = False
        
    async def connect(self):
        """Connect to the MCP server via stdio."""
        if not stdio_client:
            print("Warning: mcp library not found. Mocking MongoDB MCP connection.")
            return

        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        
        server_params = StdioServerParameters(
            command=self.server_cmd,
            args=self.server_args,
            env={"MONGODB_URI": os.getenv("MONGODB_URI", "")}
        )
        
        try:
            stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
            self.read, self.write = stdio_transport
            self.session = await self._exit_stack.enter_async_context(ClientSession(self.read, self.write))
            await self.session.initialize()
            self._connected = True
            print("Successfully connected to MongoDB MCP server.")
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
            self._connected = False

    async def get_tools(self) -> List[Any]:
        """Fetch available tools from the MCP server."""
        if not self._connected:
            # Return mock tools for the IBM hackathon demo if not connected
            return [
                {
                    "name": "search_calendar",
                    "description": "Searches the user's calendar for events.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Date or time to search"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "query_faq",
                    "description": "Queries the user's personal FAQ database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string", "description": "The question asked by the caller"}
                        },
                        "required": ["question"]
                    }
                }
            ]
            
        try:
            response = await self.session.list_tools()
            return response.tools
        except Exception as e:
            print(f"Error fetching tools: {e}")
            return []

    async def call_tool(self, name: str, arguments: dict) -> Any:
        """Call a tool on the MCP server."""
        if not self._connected:
            # Mock responses for IBM hackathon purposes
            if name == "search_calendar":
                return "The calendar shows availability for that time. Todd is free."
            elif name == "query_faq":
                return "Todd prefers to be reached via email for non-urgent matters."
            return "Tool executed successfully."
            
        try:
            result = await self.session.call_tool(name, arguments)
            return result
        except Exception as e:
            print(f"Error calling tool {name}: {e}")
            return f"Error executing tool: {str(e)}"
            
    async def cleanup(self):
        """Clean up the MCP connection."""
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._connected = False
