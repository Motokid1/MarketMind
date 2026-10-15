import asyncio
import time
import pytest
from app.core import settings,DomainError
from app.gateway import Gateway
from app.mock import install_mock
from conftest import account

def test_outage_retains_only_verified_unexpired_matching_observation(client,monkeypatch):
    gateway=Gateway();install_mock(gateway)
    monkeypatch.setattr(settings,'retries',0)
    async def run():
        first=await gateway.call('L04',{'symbol':'ALPHA'})
        key=next(iter(gateway.verified));stamp=time.monotonic()-settings.ttl-1
        gateway.cache[key]=(stamp,first);gateway.verified[key]=(stamp,first)
        async def fail(tool,args):raise TimeoutError()
        gateway.transport=fail
        retained=await gateway.call('L04',{'symbol':'ALPHA'})
        assert retained['value']==first['value']
        assert retained['source_as_of']==first['source_as_of']
        assert retained['received_at']==first['received_at']
        assert retained['status']=='stale' and retained['availability']=='stale_cache'
        assert retained['cache_age_seconds']>=settings.ttl
        with pytest.raises(DomainError):await gateway.call('L04',{'symbol':'BETA'})
        gateway.verified[key]=(time.monotonic()-settings.stale_ttl-1,first)
        with pytest.raises(DomainError):await gateway.call('L04',{'symbol':'ALPHA'},refresh=True)
    asyncio.run(run())

def test_force_retry_fetches_only_selected_panel(client,monkeypatch):
    from app.main import gateway
    original=gateway.call;called=[]
    async def call(cap,params,run_id=None,refresh=False):
        called.append((cap,refresh));return await original(cap,params,run_id,refresh=refresh)
    monkeypatch.setattr(gateway,'call',call)
    result=client.get('/api/v1/market/overview?capability=L02&refresh=true',headers=account(client))
    assert result.status_code==200
    assert list(result.json()['sections'])==['L02']
    assert called==[('L02',True)]

def test_schema_change_never_reuses_cached_numeric_values(client):
    gateway=Gateway();install_mock(gateway)
    async def run():
        await gateway.call('L04',{'symbol':'ALPHA'})
        tool=gateway.registry.select('L04')
        gateway.registry.tools[tool['id']].update(enabled=False,status='SCHEMA_CHANGED',schema_hash='changed')
        with pytest.raises(DomainError):await gateway.call('L04',{'symbol':'ALPHA'})
    asyncio.run(run())

def test_source_status_requires_auth_and_reports_ephemeral_cache(client):
    assert client.get('/api/v1/market/source-status').status_code==401
    data=client.get('/api/v1/market/source-status',headers=account(client)).json()
    assert data['cache_policy']['maximum_entries']==256
    assert 'cleared on restart' in data['cache_policy']['storage']

def test_restart_has_no_invented_cached_observations(client):
    assert not Gateway().verified

def test_discovery_outage_preserves_previously_reviewed_evidence_without_invoking_disabled_tool(client):
    gateway=Gateway();install_mock(gateway)
    async def run():
        first=await gateway.call('L04',{'symbol':'ALPHA'})
        tool=gateway.registry.select('L04')
        gateway.registry.bindings['L04']={'id':tool['id'],'schema_hash':tool['schema_hash']}
        gateway.registry.tools[tool['id']].update(enabled=False,status='DISCOVERY_FAILED')
        retained=await gateway.call('L04',{'symbol':'ALPHA'})
        assert retained['value']==first['value']
        assert retained['refresh_error']=='DISCOVERY_FAILED'
        assert retained['status']=='stale'
    asyncio.run(run())

def test_shared_market_cache_does_not_leak_private_research_questions(client):
    gateway=Gateway();install_mock(gateway)
    async def run():
        first=await gateway.call('L04',{'symbol':'ALPHA','query':'Private investor question'})
        second=await gateway.call('L04',{'symbol':'ALPHA','query':'Different private question'})
        assert 'query' not in first['query_params'] and 'query' not in second['query_params']
        assert second['received_at']==first['received_at']
        assert 'Private investor' not in str(second)
    asyncio.run(run())

def test_incomplete_history_preserves_received_prefix_and_warns(client,monkeypatch):
    gateway=Gateway();install_mock(gateway)
    original=gateway.call;attempts=[]
    async def call(cap,params,run_id=None):
        attempts.append(params['end'])
        if len(attempts)>1:raise DomainError('UPSTREAM_TIMEOUT','Second chunk unavailable',504,True)
        observation=await original(cap,params,run_id)
        return {**observation,'value':observation['value'][-2:],'next_end_date':'2026-10-07'}
    monkeypatch.setattr(gateway,'call',call)
    result=asyncio.run(gateway.history({'symbol':'ALPHA','start':'2026-09-01','end':'2026-10-09'}))
    assert len(result['value'])==2
    assert result['coverage_status']=='partial'
    assert 'History incomplete' in result['warnings'][0]
