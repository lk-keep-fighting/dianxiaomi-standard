"""Client authorization utilities for the Digital Chief automation tool.

This module implements the minimal client authorization flow described in
`客户端授权方案.md`.  It provides:

- Storage helpers for encrypted local persistence of the authorization state.
- A thin HTTP client that talks to the external authorization service
  (`/auth/login` and `/auth/status`).
- A background monitor that refreshes the status periodically and reacts to
  remote revocations.

The implementation intentionally keeps the cryptography lightweight (simple XOR
with a salted key + random IV) to avoid introducing heavy third‑party
dependencies while still preventing the access token from being stored in
plain text.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional, Union

import requests

__all__ = [
    "AuthClient",
    "AuthMonitor",
    "AuthState",
    "AuthStateStore",
    "AuthError",
    "AuthNetworkError",
    "AuthRevokedError",
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base exception for client authorization related failures."""


class AuthNetworkError(AuthError):
    """Raised when the authorization service is temporarily unreachable."""


class AuthRevokedError(AuthError):
    """Raised when the authorization has been explicitly revoked or expired."""


# ---------------------------------------------------------------------------
# Dataclasses & helpers
# ---------------------------------------------------------------------------


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure the datetime is timezone-aware in UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_datetime(value: Optional[Union[str, int, float]]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            # Fallback for timestamps without separators, e.g. "2024-11-16 12:00:00"
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
                try:
                    return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
    return None


def _isoformat(dt: datetime) -> str:
    return _ensure_utc(dt).isoformat()


@dataclass
class AuthState:
    """In-memory representation of the client authorization state."""

    username: str
    access_token: str
    expires_at: datetime
    account_status: str = "active"
    server_time: Optional[datetime] = None
    message: Optional[str] = None

    def to_payload(self) -> dict:
        payload = {
            "username": self.username,
            "access_token": self.access_token,
            "expires_at": _isoformat(self.expires_at),
            "account_status": self.account_status,
        }
        if self.server_time is not None:
            payload["server_time"] = _isoformat(self.server_time)
        if self.message:
            payload["message"] = self.message
        return payload

    @classmethod
    def from_payload(cls, payload: dict) -> "AuthState":
        return cls(
            username=payload["username"],
            access_token=payload["access_token"],
            expires_at=_ensure_utc(_parse_datetime(payload.get("expires_at"))),
            account_status=payload.get("account_status", "active"),
            server_time=_parse_datetime(payload.get("server_time")),
            message=payload.get("message"),
        )


# ---------------------------------------------------------------------------
# Local storage with lightweight encryption
# ---------------------------------------------------------------------------


class AuthStateStore:
    """Persist authorization state locally with lightweight encryption."""

    VERSION = 1

    def __init__(self, file_path: Path, salt: Optional[str] = None) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.salt = salt or "digital-chief-client-auth"

    # Public API ---------------------------------------------------------

    def save(self, state: AuthState) -> None:
        payload = state.to_payload()
        encrypted = self._encrypt(json.dumps(payload).encode("utf-8"), state.username)
        blob = {
            "version": self.VERSION,
            "username": state.username,
            "payload": encrypted,
        }
        self.file_path.write_text(json.dumps(blob, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.chmod(self.file_path, 0o600)
        except PermissionError:
            # On Windows the chmod call is not necessary and may fail.
            pass

    def load(self) -> Optional[AuthState]:
        if not self.file_path.exists():
            return None
        try:
            blob = json.loads(self.file_path.read_text(encoding="utf-8"))
            username = blob.get("username")
            payload_token = blob.get("payload")
            if not username or not payload_token:
                return None
            decrypted = self._decrypt(payload_token, username)
            payload = json.loads(decrypted.decode("utf-8"))
            return AuthState.from_payload(payload)
        except (OSError, ValueError, KeyError):
            return None

    def clear(self) -> None:
        try:
            if self.file_path.exists():
                self.file_path.unlink()
        except OSError:
            pass

    # Internal helpers ---------------------------------------------------

    def _derive_key(self, username: str) -> bytes:
        base = f"{self.salt}:{username}".encode("utf-8")
        return hashlib.sha256(base).digest()

    def _encrypt(self, plaintext: bytes, username: str) -> str:
        key = self._derive_key(username)
        iv = os.urandom(16)
        combined = iv + plaintext
        cipher_bytes = bytes(b ^ key[i % len(key)] for i, b in enumerate(combined))
        return base64.urlsafe_b64encode(cipher_bytes).decode("utf-8")

    def _decrypt(self, token: str, username: str) -> bytes:
        key = self._derive_key(username)
        data = base64.urlsafe_b64decode(token.encode("utf-8"))
        if not data:
            return b""
        plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return plain[16:]


# ---------------------------------------------------------------------------
# HTTP client and status monitor
# ---------------------------------------------------------------------------


class AuthClient:
    """HTTP client for the external authorization service."""

    def __init__(
        self,
        base_url: str,
        state_store: AuthStateStore,
        *,
        client_version: str = "1.0.0",
        status_interval: int = 900,
        max_status_failures: int = 3,
        retry_delay: int = 10,
        request_timeout: int = 10,
    ) -> None:
        if not base_url:
            raise ValueError("Authorization service base URL must be provided")

        self.base_url = base_url.rstrip("/")
        self.state_store = state_store
        self.client_version = client_version
        self.status_interval = max(30, int(status_interval or 900))
        self.max_status_failures = max(1, int(max_status_failures or 3))
        self.retry_delay = max(1, int(retry_delay or 5))
        self.request_timeout = max(5, int(request_timeout or 10))

        self.session = requests.Session()

        self.username: Optional[str] = None
        self.access_token: Optional[str] = None
        self.account_status: str = "unknown"
        self.message: Optional[str] = None

        self._expires_at_server: Optional[datetime] = None
        self._local_expiry: Optional[datetime] = None
        self._time_offset: timedelta = timedelta(0)

    # Public API -----------------------------------------------------

    def load_cached_state(self) -> Optional[AuthState]:
        state = self.state_store.load()
        if not state:
            return None
        try:
            self._apply_state(state)
            self._ensure_not_expired()
            return state
        except AuthRevokedError:
            self.clear_cached_state()
            return None

    def clear_cached_state(self) -> None:
        self.state_store.clear()
        self.username = None
        self.access_token = None
        self.account_status = "unknown"
        self._expires_at_server = None
        self._local_expiry = None
        self.message = None

    def login(self, username: str, password: str) -> AuthState:
        payload = {
            "username": username,
            "password": password,
            "client_version": self.client_version,
        }
        url = f"{self.base_url}/auth/login"
        try:
            response = self.session.post(url, json=payload, timeout=self.request_timeout)
        except requests.RequestException as exc:
            raise AuthNetworkError(f"无法连接授权服务: {exc}") from exc

        data = self._extract_payload(response)
        state = self._state_from_login_response(username, data)
        self._apply_state(state)
        self._ensure_not_expired()
        self.state_store.save(state)
        return state

    def check_status(self) -> AuthState:
        if not self.access_token:
            raise AuthError("Access token is missing; please login first")

        url = f"{self.base_url}/auth/status"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            response = self.session.get(url, headers=headers, timeout=self.request_timeout)
        except requests.RequestException as exc:
            raise AuthNetworkError(f"授权状态检查失败: {exc}") from exc

        data = self._extract_payload(response)
        state = self._state_from_status_response(data)
        self._apply_state(state)
        self._ensure_not_expired()
        self.state_store.save(state)
        return state

    def get_local_expiry(self) -> Optional[datetime]:
        return self._local_expiry

    def local_expiry_iso(self) -> Optional[str]:
        if not self._local_expiry:
            return None
        return _isoformat(self._local_expiry)

    def start_status_monitor(
        self,
        *,
        on_revoked: Optional[Callable[[str], None]] = None,
        on_warning: Optional[Callable[[str], None]] = None,
    ) -> "AuthMonitor":
        if not self.access_token:
            raise AuthError("Cannot start status monitor before login")
        monitor = AuthMonitor(
            client=self,
            interval=self.status_interval,
            max_failures=self.max_status_failures,
            retry_delay=self.retry_delay,
            on_revoked=on_revoked,
            on_warning=on_warning,
        )
        monitor.start()
        return monitor

    # Internal helpers ------------------------------------------------

    def _extract_payload(self, response: requests.Response) -> dict:
        try:
            data = response.json()
        except ValueError as exc:
            text = response.text.strip()
            raise AuthError(f"授权服务返回了无效的响应: {text}") from exc

        if response.status_code >= 400:
            message = data.get("message") or data.get("error") or f"HTTP {response.status_code}"
            if response.status_code == 401:
                raise AuthRevokedError(message)
            raise AuthError(message)
        return data

    def _state_from_login_response(self, username: str, data: dict) -> AuthState:
        token = data.get("access_token")
        expires_at = _parse_datetime(data.get("expires_at"))
        account_status = data.get("account_status", "active")
        if not token or not expires_at:
            raise AuthError("授权服务返回数据缺失")
        if account_status.lower() != "active":
            raise AuthRevokedError(data.get("message") or "账号已被禁用")

        state = AuthState(
            username=username,
            access_token=token,
            expires_at=_ensure_utc(expires_at),
            account_status=account_status,
            server_time=_parse_datetime(data.get("server_time")),
            message=data.get("message"),
        )
        return state

    def _state_from_status_response(self, data: dict) -> AuthState:
        token = data.get("access_token", self.access_token)
        expires_at = _parse_datetime(data.get("expires_at")) or self._expires_at_server
        account_status = data.get("account_status", self.account_status or "active")
        if not token or not expires_at:
            raise AuthError("授权状态响应缺少必要字段")
        state = AuthState(
            username=self.username or "",
            access_token=token,
            expires_at=_ensure_utc(expires_at),
            account_status=account_status,
            server_time=_parse_datetime(data.get("server_time")),
            message=data.get("message"),
        )
        if account_status.lower() != "active":
            msg = state.message or "账号已被禁用"
            raise AuthRevokedError(msg)
        return state

    def _apply_state(self, state: AuthState) -> None:
        self.username = state.username
        self.access_token = state.access_token
        self.account_status = state.account_status
        self.message = state.message

        if state.server_time is not None:
            now = datetime.now(timezone.utc)
            self._time_offset = state.server_time.astimezone(timezone.utc) - now

        self._expires_at_server = _ensure_utc(state.expires_at)
        self._local_expiry = self._convert_to_local(self._expires_at_server)

    def _convert_to_local(self, server_dt: datetime) -> datetime:
        server_dt = _ensure_utc(server_dt)
        return server_dt - self._time_offset

    def _ensure_not_expired(self) -> None:
        if not self._local_expiry:
            return
        now = datetime.now(timezone.utc)
        if self._local_expiry <= now:
            raise AuthRevokedError("授权已到期，请联系管理员续期")


class AuthMonitor:
    """Background task that periodically checks authorization status."""

    def __init__(
        self,
        *,
        client: AuthClient,
        interval: int,
        max_failures: int,
        retry_delay: int,
        on_revoked: Optional[Callable[[str], None]] = None,
        on_warning: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.client = client
        self.interval = interval
        self.max_failures = max_failures
        self.retry_delay = retry_delay
        self.on_revoked = on_revoked
        self.on_warning = on_warning

        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._run, name="AuthMonitor", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=self.retry_delay + 1)

    # Internal --------------------------------------------------------

    def _run(self) -> None:
        failure_count = 0
        while not self._stop_event.wait(self.interval):
            if self._stop_event.is_set():
                break
            try:
                self.client.check_status()
                failure_count = 0
            except AuthNetworkError as exc:
                failure_count += 1
                if failure_count >= self.max_failures:
                    if self.on_warning:
                        self.on_warning(str(exc))
                    else:
                        print(f"⚠️ 授权状态检查连续失败: {exc}")
                    failure_count = 0
                if self._stop_event.wait(self.retry_delay):
                    break
            except AuthRevokedError as exc:
                if self.on_revoked:
                    self.on_revoked(str(exc))
                else:
                    print(f"❌ 授权已失效: {exc}")
                break
            except AuthError as exc:
                # Treat other auth errors as revoked to be safe
                if self.on_revoked:
                    self.on_revoked(str(exc))
                else:
                    print(f"❌ 授权异常: {exc}")
                break

        # Ensure the thread exits once stop is requested
        self._stop_event.set()
