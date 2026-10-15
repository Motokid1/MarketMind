import pytest
from datetime import timedelta
from app.core import now
from app.core import DomainError
from app.nse_adapters import adapt

TOOL={'parser':'current_movers','service':'cmmkt'}

def test_reviewed_stock_record_shape_requires_exchange_time_not_crawl_time():
    row={'symbol':'ALPHA','lastTradedPrice':100,'perChange':2,'volume':50}
    assert adapt(TOOL,{'updatedAt':'2026-10-14T09:00:00Z','stocks':[row]}, {})['value'] is None
    output=adapt(TOOL,{'nseTimestamp':'13-Oct-2026 15:30:00','stocks':[row]}, {})
    assert output['value'][0]['price']=='100'
    assert output['value'][0]['change_percent']=='2'

def test_per_row_dates_are_preserved_and_envelope_uses_earliest_observation():
    rows=[{'symbol':'ALPHA','lastTradedPrice':100,'perChange':2,'latestTimestamp':'2026-10-13 15:30:00'},{'symbol':'BETA','lastTradedPrice':200,'perChange':3,'latestTimestamp':'2026-10-13 15:29:00'}]
    output=adapt(TOOL,{'stocks':rows}, {})
    assert output['source_as_of']=='2026-10-13T15:29:00+05:30'
    assert output['value'][0]['source_as_of']=='2026-10-13T15:30:00+05:30'

def test_source_error_is_not_misreported_as_missing_timestamp():
    with pytest.raises(DomainError) as exc:adapt(TOOL,{'error':'fetch failed'}, {})
    assert exc.value.code=='UPSTREAM_ERROR' and exc.value.retryable

def test_non_finite_movers_are_rejected():
    with pytest.raises(DomainError):adapt(TOOL,{'nseTimestamp':'13-Oct-2026 15:30:00','stocks':[{'symbol':'ALPHA','price':'NaN','change_percent':2}]}, {})

def test_dated_quote_without_price_is_not_a_verified_observation():
    output=adapt({'parser':'quote','service':'cmmkt'},{'stock':{'latestTimestamp':'2026-10-13 15:30:00','lastTradedPrice':None}}, {})
    assert output['value'] is None

def test_non_finite_index_is_rejected_before_cache():
    with pytest.raises(DomainError):adapt({'parser':'index','service':'cmmkt'},{'nseTimestamp':'13-Oct-2026 15:30:00','index':{'indexName':'NIFTY 50','last':'NaN'}}, {})

def test_date_only_current_record_has_no_invented_tick_time():
    output=adapt(TOOL,{'nseTimestamp':'2026-10-13','stocks':[{'symbol':'ALPHA','price':100,'change_percent':2}]}, {})
    assert output['source_as_of'] is None and output['value'] is None

def test_naive_iso_current_timestamp_is_not_treated_as_timezone_verified():
    output=adapt(TOOL,{'stocks':[{'symbol':'ALPHA','price':100,'change_percent':2,'latestTimestamp':'2026-10-13T15:30:00'}]}, {})
    assert output['source_as_of'] is None and output['value'] is None

def test_future_row_is_rejected_even_with_valid_batch_timestamp():
    with pytest.raises(DomainError) as exc:
        adapt(TOOL,{'nseTimestamp':'13-Oct-2026 15:30:00','stocks':[{'symbol':'ALPHA','price':100,'change_percent':2,'latestTimestamp':(now()+timedelta(days=1)).isoformat()}]}, {})
    assert exc.value.code=='INVALID_SOURCE_TIME'
