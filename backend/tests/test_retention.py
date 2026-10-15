from datetime import timedelta
from conftest import account
from app.db import Session, Report
from app.core import now
def test_expired_derived_records_purged(client):
    owner=account(client); admin=account(client,'admin@example.test')
    run=client.post('/api/v1/research/runs',headers=owner,json={'symbols':['ALPHA'],'start':'2026-09-01','end':'2026-10-09'}).json()
    with Session() as db:
        report=db.get(Report,run['report_id']);report.retention_until=now()-timedelta(days=1);db.commit()
    result=client.post('/api/v1/admin/retention/purge',headers=admin)
    assert result.status_code==200,result.text
    assert result.json()['deleted_reports']==1
    assert client.get('/api/v1/research/runs/'+run['id'],headers=owner).status_code==404
