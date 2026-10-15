from decimal import Decimal as D
import pytest
from app.analytics import metrics, compare
from app.core import Portfolio
def test_AT004_independent_return_and_drawdown():
    rows=[{'close':D(p),'volume':D(100),'date':str(i)} for i,p in enumerate(('100','120','90','108'))]
    m=metrics(rows)
    assert D(m['return_percent'])==D('8')
    assert D(m['max_drawdown_percent'])==D('-25')
def test_AT005_alignment():
    def obs(symbol,days):
        return {'instrument':symbol,'value':[{'date':d,'close':'100','volume':'0'} for d in days],'status':'historical','evidence_id':symbol,'source_as_of':'2026-10-09T10:00:00+00:00'}
    result=compare([obs('A',['2026-10-01','2026-10-02']),obs('B',['2026-10-02','2026-10-05'])])
    assert result['sessions']==['2026-10-02']
    assert result['metrics'][0]['return_percent'] is None
    assert result['metrics'][0]['missing_sessions']==['2026-10-05']
def test_AT012_invalid_weights():
    with pytest.raises(ValueError):
        Portfolio(symbols=['ALPHA','BETA'],weights=['0.8','0.8'])
def test_volume_uses_only_prior_sessions():
    series=[{'close':D(100),'volume':D(100),'date':str(i)} for i in range(21)]
    series[-1]['volume']=D(1000)
    assert D(metrics(series)['volume_ratio'])==10
