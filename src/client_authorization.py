"""Client-side authorization management.

This module is responsible for ensuring that the automation script validates the
client license against the Supabase backend before executing the core logic in
``src/main.py``. The validation result is cached locally and refreshed at least
once per day so that account state changes (disablement, expiration) take effect
promptly while avoiding unnecessary network calls on every launch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, Optional

import requests

try:  # pragma: no cover - runtime fallback when packaged differently
    from runtime_env import get_env
except ImportError:  # pragma: no cover
    from .runtime_env import get_env  # type: ignore

try:  # pragma: no cover - lazy optional import
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover - handled during runtime validation
    bcrypt = None  # type: ignore


UTC = timezone.utc


class ClientAuthorizationError(RuntimeError):
    """Raised when the client authorization flow fails."""


@dataclass
class AuthorizationState:
    """Structured representation of the cached authorization result."""

    username: str
    status: str
    expires_at: datetime
    validated_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "username": self.username,
            "status": self.status,
            "expires_at": self.expires_at.astimezone(UTC).isoformat(),
            "validated_at": self.validated_at.astimezone(UTC).isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthorizationState":
        return cls(
            username=data["username"],
            status=data["status"],
            expires_at=_parse_datetime(data["expires_at"]),
            validated_at=_parse_datetime(data["validated_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Credentials:
    username: str
    password: str


class ClientAuthorizationManager:
    """Coordinates the end-to-end client authorization lifecycle."""

    STATE_FILENAME = "client_authorization_state.json"

    def __init__(self, state_dir: Optional[Path] = None) -> None:
        base_dir = Path(__file__).resolve().parent
        project_root = base_dir.parent
        default_state_dir = project_root / "data" / "auth_states"
        self.state_dir = (state_dir or default_state_dir).resolve()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.state_dir / self.STATE_FILENAME

        self.supabase_url = self._require_env("SUPABASE_URL")
        self.supabase_api_key = self._require_env("SUPABASE_API_KEY")
        self.supabase_table = get_env("SUPABASE_CLIENT_TABLE", "client_licenses") or "client_licenses"
        self.username_column = get_env("SUPABASE_USERNAME_COLUMN", "username") or "username"
        self.password_column = get_env("SUPABASE_PASSWORD_COLUMN", "password_hash") or "password_hash"
        self.status_column = get_env("SUPABASE_STATUS_COLUMN", "status") or "status"
        self.expires_column = get_env("SUPABASE_EXPIRES_COLUMN", "expires_at") or "expires_at"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def ensure_authorized(self) -> AuthorizationState:
        """Ensure the client is authorized for the current day.

        - Uses cached state if it is still valid today and the license has not
          expired.
        - Otherwise, collects credentials, validates them against Supabase and
          refreshes the cached state.
        """

        cached_state = self._load_state()
        env_username = get_env("CLIENT_AUTH_USERNAME")
        if cached_state and env_username and env_username != cached_state.username:
            cached_state = None

        now = datetime.now(UTC)
        if cached_state and self._is_state_valid_for_today(cached_state, now):
            print(
                f"🔐 授权有效（账号: {cached_state.username}，有效期至 "
                f"{cached_state.expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M:%SZ')}）。"
            )
            return cached_state

        credentials = self._collect_credentials(cached_state)
        record = self._fetch_user_record(credentials.username)
        self._verify_password(credentials.password, record)

        refreshed_state = self._build_state(record, credentials.username, now)
        self._save_state(refreshed_state)
        print(
            f"✅ 授权校验成功（账号: {refreshed_state.username}，"
            f"有效期至 {refreshed_state.expires_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M:%SZ')}）。"
        )
        return refreshed_state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_state(self) -> Optional[AuthorizationState]:
        if not self.state_path.exists():
            return None
        try:
            with self.state_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            return AuthorizationState.from_dict(payload)
        except Exception as exc:  # pragma: no cover - defensive
            print(
                f"⚠️ 授权状态文件损坏或不可读取（{self.state_path}），将进行重新验证。原因: {exc}"
            )
            try:
                self.state_path.unlink()
            except OSError:
                pass
            return None

    def _save_state(self, state: AuthorizationState) -> None:
        payload = state.to_dict()
        with self.state_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def _collect_credentials(
        self, cached_state: Optional[AuthorizationState]
    ) -> Credentials:
        env_username = (get_env("CLIENT_AUTH_USERNAME") or "").strip()
        env_password = get_env("CLIENT_AUTH_PASSWORD", "") or ""

        username: str
        if env_username:
            username = env_username
        else:
            default_username = cached_state.username if cached_state else ""
            prompt = "请输入授权账号"
            if default_username:
                prompt += f" [{default_username}]"
            prompt += ": "
            entered = input(prompt).strip()
            username = entered or default_username

        if not username:
            raise ClientAuthorizationError("未提供授权账号，无法继续运行。")

        if env_password:
            password = env_password
        else:
            password = getpass("请输入授权密码: ")

        password = password.strip()
        if not password:
            raise ClientAuthorizationError("未提供授权密码，无法继续运行。")

        return Credentials(username=username, password=password)

    def _fetch_user_record(self, username: str) -> Dict[str, Any]:
        resource = f"{self.supabase_url.rstrip('/')}/rest/v1/{self.supabase_table}"
        params = {
            self.username_column: f"eq.{username}",
            "select": "*",
            "limit": 1,
        }
        headers = {
            "apikey": self.supabase_api_key,
            "Authorization": f"Bearer {self.supabase_api_key}",
            "Accept": "application/json",
        }
        try:
            response = requests.get(resource, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            records = response.json()
        except requests.RequestException as exc:
            raise ClientAuthorizationError(f"无法连接 Supabase 服务: {exc}") from exc
        except ValueError as exc:
            raise ClientAuthorizationError("Supabase 返回了无法解析的响应，请稍后重试。") from exc

        if not isinstance(records, list) or not records:
            raise ClientAuthorizationError("授权账号不存在或已被移除。")

        return records[0]

    def _verify_password(self, password: str, record: Dict[str, Any]) -> None:
        stored_secret = record.get(self.password_column) or record.get("password")
        if stored_secret is None:
            raise ClientAuthorizationError("授权数据缺少密码信息，请联系管理员。")

        if isinstance(stored_secret, str) and stored_secret.startswith("$2"):
            if bcrypt is None:
                raise ClientAuthorizationError(
                    "服务器使用 bcrypt 哈希，但客户端缺少 bcrypt 依赖。请执行 `pip install bcrypt` 后重试。"
                )
            if not bcrypt.checkpw(password.encode("utf-8"), stored_secret.encode("utf-8")):
                raise ClientAuthorizationError("授权密码错误，请重新输入。")
            return

        if stored_secret != password:
            raise ClientAuthorizationError("授权密码错误，请重新输入。")

    def _build_state(
        self, record: Dict[str, Any], username: str, now: datetime
    ) -> AuthorizationState:
        expires_raw = record.get(self.expires_column)
        if not expires_raw:
            raise ClientAuthorizationError("授权账号缺少有效期信息，请联系管理员。")

        expires_at = _parse_datetime(expires_raw)
        if expires_at <= now:
            raise ClientAuthorizationError("授权账号已过期，请联系管理员续期。")

        status_value = record.get(self.status_column, "active")
        normalized_status = str(status_value).strip().lower()
        if normalized_status in {"disabled", "inactive", "false", "0"}:
            raise ClientAuthorizationError("授权账号已被禁用，请联系管理员。")
        if normalized_status not in {"active", "enabled", "true", "1"}:
            raise ClientAuthorizationError("无法识别的账号状态，请联系管理员。")
        canonical_status = "active"

        metadata = self._sanitize_record(record)
        return AuthorizationState(
            username=username,
            status=canonical_status,
            expires_at=expires_at,
            validated_at=now,
            metadata=metadata,
        )

    def _sanitize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        sanitized = {
            key: value
            for key, value in record.items()
            if key not in {self.password_column, "password"}
        }
        return sanitized

    def _is_state_valid_for_today(
        self, state: AuthorizationState, now: datetime
    ) -> bool:
        if state.expires_at <= now:
            return False
        return state.validated_at.date() == now.date()

    @staticmethod
    def _require_env(name: str) -> str:
        value = get_env(name)
        if not value:
            raise ClientAuthorizationError(f"缺少必要的环境变量 {name}。")
        return value


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(value, tz=UTC)
    elif isinstance(value, str):
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    else:  # pragma: no cover - defensive
        raise ClientAuthorizationError(f"无法解析日期时间：{value!r}")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


_AUTHORIZATION_CONFIRMED = False


def ensure_client_authorized() -> AuthorizationState:
    """Module-level helper to ensure authorization is performed once per run."""

    global _AUTHORIZATION_CONFIRMED
    if _AUTHORIZATION_CONFIRMED:
        if _CACHED_STATE is None:
            raise ClientAuthorizationError("授权状态不可用。")
        return _CACHED_STATE

    manager = ClientAuthorizationManager()
    state = manager.ensure_authorized()
    _AUTHORIZATION_CONFIRMED = True
    _cache_state(state)
    return state


_CACHED_STATE: Optional[AuthorizationState] = None


def _cache_state(state: AuthorizationState) -> None:
    global _CACHED_STATE
    _CACHED_STATE = state
