"""AT-001: every actual discovered input schema checked offline; no network in CI."""
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator, validate
from app.gateway import RegistryStore, Gateway
from app.nse_adapters import adapt

manifest=json.loads((Path(__file__).resolve().parents[1]/'specs/generated/nse-tool-manifest.json').read_text())
tools=[(service,tool) for service,data in manifest['services'].items() for tool in data['tools']]
@pytest.mark.parametrize('service,tool',tools,ids=[s+':'+t['name'] for s,t in tools])
def test_discovered_schema_unknown_disabled(service,tool):
    Draft202012Validator.check_schema(tool['inputSchema'])
    registry=RegistryStore(); registry.sync(service,[tool])
    assert not registry.tools[service+':'+tool['name']]['enabled']
    arguments={k:('RELIANCE' if k=='symbol' else '2026-10-09' if 'date' in k.lower() else 1 if v.get('type')=='integer' else ['RELIANCE','TCS'] if v.get('type')=='array' else '') for k,v in tool['inputSchema']['properties'].items()}
    validate(arguments,tool['inputSchema'])
def test_reviewed_capability_coverage_and_hashes(client):
    gateway=Gateway()
    for service,entry in manifest['services'].items():gateway.registry.sync(service,entry['tools'])
    gateway.load_reviewed_bindings()
    assert len(gateway.registry.bindings)==19
    for capability,binding in gateway.registry.bindings.items():
        assert gateway.registry.select(capability)['schema_hash']==binding['schema_hash']
    assert not gateway.registry.tools['bhavcopy:get_corporate_actions']['enabled']
def test_historical_adapter_uses_actual_source_date():
    output=adapt({'parser':'history','service':'bhavcopy'},{'to_date':'2026-10-09','data':[{'date':'2026-10-08','close':100,'volume':10},{'date':'2026-10-09','close':110,'volume':12}]},{'start':'2026-10-01','end':'2026-10-09'})
    assert output['source_as_of']=='2026-10-09T15:30:00+05:30'
    assert output['value'][-1]['close']=='110'
def test_live_quote_does_not_use_crawl_date():
    output=adapt({'parser':'quote','service':'cmmkt'},{'updatedAt':'2026-10-11T07:00:00Z','stock':{'latestTimestamp':'2026-10-09 16:00:27','lastTradedPrice':100}},{})
    assert output['source_as_of']=='2026-10-09T16:00:27+05:30'
    assert output['value']['price']=='100'

def test_quote_preserves_returned_market_fields():
    output=adapt({'parser':'quote','service':'cmmkt'},{'stock':{'symbol':'TCS','latestTimestamp':'2026-10-09 16:00:27','lastTradedPrice':100,'perChange':-2.1,'volume':123,'fiftyTwoWeekHigh':150,'fiftyTwoWeekLow':80}},{})
    assert output['value']['change_percent']=='-2.1'
    assert output['value']['volume']=='123'
    assert output['value']['52_week_high']=='150'
    assert output['value']['52_week_low']=='80'
def test_bare_price_has_no_invented_timestamp():
    assert adapt({'parser':'undated_scalar','service':'bhavcopy'},125.5,{'end':'2026-10-09'})['value'] is None
