"""Unit tests for the lightweight client authorization helpers."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.append(str(CURRENT_DIR))

from auth_client import AuthClient, AuthState, AuthStateStore


def _make_state(username: str = "demo-user") -> AuthState:
    now = datetime.now(timezone.utc)
    return AuthState(
        username=username,
        access_token="sample-token",
        expires_at=now + timedelta(hours=2),
        account_status="active",
        server_time=now,
        message="ok",
    )


def test_auth_state_store_round_trip(tmp_path: Path) -> None:
    store = AuthStateStore(tmp_path / "state.enc", salt="unit-test-salt")
    original = _make_state()

    store.save(original)
    loaded = store.load()

    assert loaded is not None
    assert loaded.username == original.username
    assert loaded.access_token == original.access_token
    assert loaded.account_status == original.account_status
    assert loaded.message == original.message
    assert abs((loaded.expires_at - original.expires_at).total_seconds()) < 1


def test_auth_state_store_clear(tmp_path: Path) -> None:
    store = AuthStateStore(tmp_path / "state.enc", salt="unit-test-salt")
    store.save(_make_state())

    assert store.load() is not None
    store.clear()
    assert store.load() is None


def test_auth_client_load_cached_state(tmp_path: Path) -> None:
    store = AuthStateStore(tmp_path / "state.enc", salt="unit-test-salt")
    client = AuthClient(
        base_url="https://example.com",
        state_store=store,
        client_version="test",
        status_interval=900,
        retry_delay=5,
        request_timeout=5,
    )

    store.save(_make_state("cached-user"))
    cached = client.load_cached_state()

    assert cached is not None
    assert client.access_token == cached.access_token
    assert client.username == cached.username
    assert client.get_local_expiry() is not None
