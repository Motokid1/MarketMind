"""Offline integration server, explicitly synthetic; not an NSE emulator claim."""
from mcp.server.fastmcp import FastMCP
from app.mock import mock_transport

server=FastMCP('MarketMind synthetic contract fixtures',host='127.0.0.1',port=8765)
@server.tool()
async def synthetic_history(symbol:str,start:str,end:str):
    return await mock_transport({'service':'bhavcopy','capability':'B02'},{'symbol':symbol,'start':start,'end':end})
@server.tool()
async def synthetic_quote(symbol:str):
    return await mock_transport({'service':'cmmkt','capability':'L04'},{'symbol':symbol})
if __name__=='__main__':
    server.run(transport='streamable-http')
