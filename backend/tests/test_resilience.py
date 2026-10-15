import asyncio
import time
import pytest
from app.gateway import Gateway
from app.mock import install_mock
from app.workflow import execute
from app.core import DomainError

def test_fully_unavailable_is_explicit_degraded(client):
    result=asyncio.run(execute(Gateway(),'trace','owner',{'symbols':['ALPHA'],'start':'2026-09-01','end':'2026-10-09','source':'historical','query':'Research','index':'NIFTY 50'}))
    assert result['status']=='degraded'
    assert not result['final']['claims']
    assert result['warnings']
def test_graph_budget_never_exceeds_twelve_calls(client):
    gateway=Gateway(); install_mock(gateway)
    counter=[]; transport=gateway.transport
    async def wrapped(tool,args):
        counter.append(tool['name']);return await transport(tool,args)
    gateway.transport=wrapped
    state=asyncio.run(execute(gateway,'trace','owner',{'symbols':['ALPHA','BETA'],'start':'2026-09-01','end':'2026-10-09','source':'current','query':'Briefing','index':'NIFTY 50'}))
    assert len(counter)<=12 and state['evidence_ids']
def test_cache_preserves_received_at(client):
    gateway=Gateway();install_mock(gateway)
    async def run():
        first=await gateway.call('L04',{'symbol':'ALPHA'})
        second=await gateway.call('L04',{'symbol':'ALPHA'})
        assert first['received_at']==second['received_at']
        assert second['cache_age_seconds']>=0
    asyncio.run(run())
def test_cached_quote_panel_latency(client):
    gateway=Gateway();install_mock(gateway)
    async def run():
        await gateway.call('L04',{'symbol':'ALPHA'})
        durations=[]
        for _ in range(30):
            start=time.perf_counter();await gateway.call('L04',{'symbol':'ALPHA'});durations.append(time.perf_counter()-start)
        assert sorted(durations)[int(.95*len(durations))-1]<8
    asyncio.run(run())
def test_advice_rejected_before_tools(client):
    gateway=Gateway();install_mock(gateway)
    with pytest.raises(DomainError):
        asyncio.run(execute(gateway,'trace','owner',{'symbols':[],'start':'2026-09-01','end':'2026-10-09','source':'current','query':'buy ALPHA','index':'NIFTY 50'}))

def test_failed_symbol_resolution_does_not_retrieve_unverified_equity_history(client):
    gateway=Gateway();install_mock(gateway)
    original=gateway.transport;called=[]
    async def transport(tool,args):
        called.append(tool['capability'])
        if tool['capability']=='B01':raise DomainError('SOURCE_UNAVAILABLE','Universe lookup unavailable',503,True)
        return await original(tool,args)
    gateway.transport=transport
    result=asyncio.run(execute(gateway,'trace','owner',{'symbols':['ALPHA'],'start':'2026-09-01','end':'2026-10-09','source':'historical','query':'Research','index':'NIFTY 50'}))
    assert 'B02' not in called
    assert not result['metrics']['metrics']
    assert any('symbol resolution unavailable' in w for w in result['warnings'])
