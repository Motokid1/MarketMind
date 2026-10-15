from conftest import account

def test_export_links_every_claim_to_dated_evidence_and_escapes_query(client):
    auth=account(client)
    run=client.post('/api/v1/research/runs',headers=auth,json={'symbols':['ALPHA','BETA'],'start':'2026-09-01','end':'2026-10-09','query':'<script>alert(1)</script>','source':'historical'}).json()
    exported=client.get('/api/v1/reports/'+run['report_id']+'/export',headers=auth).text
    assert '<script>alert(1)</script>' not in exported
    assert 'Key findings' in exported and 'Coverage and limitations' in exported
    for claim in run['result']['final']['claims']:
        for ref in claim['evidence_ids']:
            assert f'href="#evidence-{ref}"' in exported
            assert f'id="evidence-{ref}"' in exported
