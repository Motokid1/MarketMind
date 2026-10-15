from conftest import account
from app.main import gateway

def test_missing_current_movers_use_explicitly_dated_historical_replay(client,monkeypatch):
    original=gateway.call
    async def call(cap,params,run_id=None):
        if cap in ('L01','L05'):
            return {'value':None,'status':'missing','source_as_of':None}
        result=await original(cap,params,run_id)
        if cap=='L02':result={**result,'source_as_of':'2026-10-09T10:00:00+00:00'}
        return result
    monkeypatch.setattr(gateway,'call',call)
    result=client.get('/api/v1/market/overview',headers=account(client)).json()
    for cap in ('L01','L05'):
        observation=result['sections'][cap]
        assert observation['value']
        assert observation['historical_fallback']
        assert observation['service']=='bhavcopy'
        assert observation['status']=='historical'
        assert '2026-10-09' in observation['warnings'][0]
