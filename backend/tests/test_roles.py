from conftest import account
from app.db import Session, User
from sqlalchemy import select
SCOPE={'symbols':['ALPHA'],'start':'2026-09-01','end':'2026-10-09','query':'Research','source':'historical'}
def test_explicit_reviewer_share_only(client):
    owner=account(client); reviewer=account(client,'reviewer@example.test'); stranger=account(client,'stranger@example.test')
    with Session() as db:
        target=db.scalar(select(User).where(User.email=='reviewer@example.test'));target.role='reviewer';reviewer_id=target.id;db.commit()
    run=client.post('/api/v1/research/runs',headers=owner,json=SCOPE).json()
    report=run['report_id']
    assert client.get('/api/v1/reports/'+report,headers=reviewer).status_code==404
    assert client.post('/api/v1/reports/'+report+'/share',headers=owner,json={'reviewer_id':reviewer_id}).status_code==200
    assert client.get('/api/v1/reports/'+report,headers=reviewer).status_code==200
    assert client.get('/api/v1/reports/'+report,headers=stranger).status_code==404
    assert client.post('/api/v1/reports/'+report+'/annotations',headers=reviewer,json={'text':'Prices are unadjusted; note corporate-action limitations.'}).status_code==200
    assert client.post('/api/v1/reports/'+report+'/annotations',headers=owner,json={'text':'not reviewer'}).status_code==422
def test_forged_token_denied(client):
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer fabricated'}).status_code==401
def test_role_cannot_be_self_assigned(client):
    owner=account(client)
    assert client.get('/api/v1/auth/me',headers=owner).json()['role']=='researcher'
    assert client.patch('/api/v1/admin/users/whatever',headers=owner,json={'role':'administrator'}).status_code==403
