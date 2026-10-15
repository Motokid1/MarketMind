import asyncio
from datetime import timedelta
import pytest
from conftest import account
from app.core import now, settings, DomainError
from app.gateway import Gateway, normalize, freshness
from app.mock import install_mock
from app.workflow import execute

SCOPE={'symbols':['ALPHA','BETA'],'start':'2026-09-01','end':'2026-10-09','query':'Compare historical observations','source':'historical'}
def test_AT002_delayed_quote(client):
    response=client.get('/api/v1/instruments/ALPHA/quote',headers=account(client)).json()
    assert response['status']=='delayed'
    assert response['source_as_of'] and response['received_at']
    assert response['synthetic'] and 'Synthetic' in response['data_delay_label']
def test_AT003_missing_quote(client):
    response=client.get('/api/v1/instruments/UNKNOWN/quote',headers=account(client)).json()
    assert response['value'] is None and 'value' in response['missing_fields']
def test_AT006_closed_session(client):
    result=client.get('/api/v1/market/overview',headers=account(client)).json()
    assert result['sections']['L08']['status']=='closed'
    assert result['sections']['L08']['value']['latest_session']=='2026-10-09'
def test_AT007_owner_isolation_and_rbac(client):
    owner=account(client); other=account(client,'other@example.test')
    result=client.post('/api/v1/research/runs',headers=owner,json=SCOPE)
    assert result.status_code==201,result.text
    run=result.json()
    assert client.get('/api/v1/research/runs/'+run['id'],headers=other).status_code==404
    assert client.get('/api/v1/reports/'+run['report_id']+'/export',headers=other).status_code==404
    assert client.get('/api/v1/admin/mcp/capabilities',headers=owner).status_code==403
    assert client.get('/api/v1/research/runs').status_code==401
def test_AT008_bounded_timeout(client,monkeypatch):
    gateway=Gateway();install_mock(gateway)
    attempts=[]
    async def fail(tool,args):
        attempts.append(1);raise TimeoutError()
    gateway.transport=fail
    monkeypatch.setattr(settings,'retries',1)
    with pytest.raises(DomainError) as exc:
        asyncio.run(gateway.call('L04',{'symbol':'ALPHA'}))
    assert exc.value.code=='UPSTREAM_TIMEOUT'
    assert len(attempts)==2
def test_AT009_injection_is_data_and_AT010_export(client):
    owner=account(client)
    result=client.post('/api/v1/research/runs',headers=owner,json=SCOPE)
    assert result.status_code==201,result.text
    run=result.json(); report=run['result']
    assert '999999' not in str(report['final'])
    assert 'buy shares' not in str(report['final'])
    assert all(c['evidence_ids'] and c['source_as_of'] and c['units'] for c in report['final']['claims'])
    exported=client.get('/api/v1/reports/'+run['report_id']+'/export',headers=owner)
    assert exported.status_code==200
    for value in (run['id'],'source_as_of','evidence_id','disclaimer','Educational','formula_version'):
        assert value in exported.text
def test_AT012_weights_api(client):
    result=client.post('/api/v1/portfolio/simulate',headers=account(client),json={**SCOPE,'weights':['0.8','0.8']})
    assert result.status_code==422
    assert result.json()['error_code']=='VALIDATION_ERROR'
def test_valid_portfolio(client):
    result=client.post('/api/v1/portfolio/simulate',headers=account(client),json={**SCOPE,'weights':['0.5','0.5'],'amount':'100000'})
    assert result.status_code==200,result.text
    assert result.json()['portfolio']['concentration_hhi']=='0.50'
def test_stale_disables_current_conclusions(client):
    assert freshness((now()-timedelta(hours=1)).isoformat(),'cmmkt')=='stale'
    gateway=Gateway();install_mock(gateway)
    original=gateway.transport
    async def stale(tool,args):
        payload=await original(tool,args)
        if tool['service']=='cmmkt':
            payload['source_as_of']=(now()-timedelta(hours=1)).isoformat()
        return payload
    gateway.transport=stale
    result=asyncio.run(execute(gateway,'trace','owner',{**SCOPE,'index':'NIFTY 50','source':'current'}))
    assert result['status']=='partial'
    assert any('stale' in w for w in result['warnings'])
def test_missing_timestamp_drops_value():
    result=normalize({'service':'cmmkt','name':'actual_discovered_name','schema_hash':'x'},{'value':'42','units':'INR'},{'symbol':'ALPHA'})
    assert result['value'] is None
def test_arbitrary_tool_and_url_unavailable(client):
    gateway=Gateway()
    with pytest.raises(DomainError):
        asyncio.run(gateway.call('L04',{'url':'http://127.0.0.1/private'}))
def test_unknown_symbol_not_guessed(client):
    result=client.post('/api/v1/research/comparisons',headers=account(client),json={**SCOPE,'symbols':['UNKNOWN','ALPHA']})
    assert result.status_code==422 and result.json()['error_code']=='INVALID_SYMBOL'
def test_admin_observability(client):
    headers=account(client,'admin@example.test')
    result=client.get('/api/v1/admin/mcp/capabilities',headers=headers)
    assert result.status_code==200
    assert len(result.json()['capabilities'])==19
