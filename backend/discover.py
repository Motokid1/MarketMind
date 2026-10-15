"""FR-002: metadata-only official MCP discovery; no guessed method names."""
import asyncio
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from mcp import ClientSession
from mcp.types import PaginatedRequestParams
from mcp.client.streamable_http import streamable_http_client

ENDPOINTS = {
    'bhavcopy': 'https://mcp.nseindia.in/bhavcopy/cm/mcp',
    'cmmkt': 'https://mcp.nseindia.in/cmmkt/mcp',
}

async def discover():
    output = {'discovered_at': datetime.now(timezone.utc).isoformat(), 'services': {}}
    for service, url in ENDPOINTS.items():
        try:
            async with asyncio.timeout(25):
                async with streamable_http_client(url) as (read, write, _):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        methods = []
                        cursor = None
                        while True:
                            page = await session.list_tools(params=PaginatedRequestParams(cursor=cursor) if cursor else None)
                            for tool in page.tools:
                                schema = tool.inputSchema
                                methods.append({'name': tool.name, 'description': tool.description,
                                                'inputSchema': schema,
                                                'schema_hash': hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()})
                            cursor = page.nextCursor
                            if not cursor:
                                break
                        output['services'][service] = {'endpoint': url, 'status': 'discovered', 'tools': methods}
        except Exception as exc:
            def leaves(error):
                return sum((leaves(e) for e in error.exceptions), []) if isinstance(error, BaseExceptionGroup) else [{'type':type(error).__name__, 'message':str(error)[:500]}]
            output['services'][service] = {'endpoint': url, 'status': 'BLOCKED', 'error_type': type(exc).__name__, 'errors':leaves(exc), 'tools': []}
    path = Path(__file__).resolve().parent / 'specs/generated/nse-tool-manifest.json'
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    asyncio.run(discover())




