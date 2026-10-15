"""T03 contract: AT-001,011; mock metadata is never an NSE manifest."""
from app.gateway import RegistryStore, schema_hash
def test_registry_requires_review_and_pins_schemas():
    r=RegistryStore()
    tool={'name':'arbitrary_actual_name','description':'history','inputSchema':{'type':'object','properties':{'ticker':{'type':'string'}},'required':['ticker']}}
    r.sync('bhavcopy',[tool])
    assert not r.tools['bhavcopy:arbitrary_actual_name']['enabled']
    r.approve('bhavcopy:arbitrary_actual_name','B02',{'symbol':'ticker'},schema_hash(tool['inputSchema']))
    assert r.tools['bhavcopy:arbitrary_actual_name']['enabled']
    tool['inputSchema']['required'].append('new_required')
    r.sync('bhavcopy',[tool])
    assert not r.tools['bhavcopy:arbitrary_actual_name']['enabled']
    assert r.alerts
