"""T02 tests written alongside identity: FR-001 / AT-007."""
from app.auth import hash_password, check_password
def test_password_storage():
    digest=hash_password('test-password')
    assert digest!='test-password'
    assert check_password('test-password',digest)
    assert not check_password('wrong-password',digest)
