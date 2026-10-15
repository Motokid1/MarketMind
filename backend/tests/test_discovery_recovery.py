import asyncio
from unittest.mock import AsyncMock
from app import main

def test_recovery_retries_failed_discovery_and_stops_on_success(monkeypatch):
    sync=AsyncMock(side_effect=[{'bhavcopy':'discovered','cmmkt':'BLOCKED'},{'bhavcopy':'discovered','cmmkt':'discovered'}])
    sleep=AsyncMock()
    monkeypatch.setattr(main.gateway,'sync',sync)
    monkeypatch.setattr(main.asyncio,'sleep',sleep)
    asyncio.run(main.recover_discovery())
    assert sync.await_count==2
    assert [call.args[0] for call in sleep.await_args_list]==[5,60]
