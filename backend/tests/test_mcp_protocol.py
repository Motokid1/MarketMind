"""Official SDK against an in-process synthetic Streamable HTTP MCP server."""
import asyncio
import json
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP

def test_mock_server_discovery_call_and_timestamp():
    server=FastMCP('synthetic-test-only',stateless_http=True,json_response=True)
    @server.tool()
    async def fictional_quote(symbol:str):
        return {'value':'123.45','source_as_of':'2026-10-09T10:00:00+00:00','units':'INR','symbol':symbol}
    app=server.streamable_http_app()
    async def run():
        async with server.session_manager.run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app)) as http:
                async with streamable_http_client('http://localhost:8765/mcp',http_client=http) as (read,write,_):
                    async with ClientSession(read,write) as session:
                        await session.initialize()
                        listed=await session.list_tools()
                        assert listed.tools[0].name=='fictional_quote'
                        assert listed.tools[0].inputSchema['required']==['symbol']
                        result=await session.call_tool('fictional_quote',{'symbol':'ALPHA'})
                        payload=result.structuredContent or json.loads(result.content[0].text)
                        assert payload['value']=='123.45'
                        assert payload['source_as_of']
    asyncio.run(run())
