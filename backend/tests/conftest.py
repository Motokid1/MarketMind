import os
import tempfile
from pathlib import Path
os.environ['MCP_MODE']='mock'
os.environ['ADMIN_EMAILS']='admin@example.test'
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'test.db').replace('\\','/')
import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app, login_attempts

@pytest.fixture
def client():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine); login_attempts.clear()
    with TestClient(app) as client:
        yield client
def account(client,email='researcher@example.test'):
    response=client.post('/api/v1/auth/register',json={'email':email,'password':'strong-test-password','acknowledged':True})
    assert response.status_code==201,response.text
    return {'Authorization':'Bearer '+response.json()['access_token']}
