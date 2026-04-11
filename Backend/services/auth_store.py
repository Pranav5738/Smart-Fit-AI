from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import status

from utils.exceptions import SmartFitError

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ITERATIONS = 210000
_HASH_SCHEME = "pbkdf2_sha256"
_PASSWORD_HAS_LOWER = re.compile(r"[a-z]")
_PASSWORD_HAS_UPPER = re.compile(r"[A-Z]")
_PASSWORD_HAS_DIGIT = re.compile(r"\d")
_PASSWORD_HAS_SYMBOL = re.compile(r"[^A-Za-z0-9]")


class AuthStoreService:
    """SQLite-backed storage for SmartFit authentication users."""

    def __init__(
        self,
        db_path: Path,
        access_token_secret: str,
        access_token_minutes: int = 20,
        refresh_token_days: int = 14,
        max_failed_attempts: int = 5,
        lockout_minutes: int = 10,
        attempt_window_minutes: int = 15,
    ) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self.access_token_secret = access_token_secret.strip()
        self.access_token_minutes = max(1, access_token_minutes)
        self.refresh_token_days = max(1, refresh_token_days)
        self.max_failed_attempts = max(1, max_failed_attempts)
        self.lockout_minutes = max(1, lockout_minutes)
        self.attempt_window_minutes = max(1, attempt_window_minutes)

        if not self.access_token_secret:
            raise ValueError("auth access token secret cannot be empty")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def register_user(
        self,
        name: str,
        email: str,
        password: str,
        height_cm: float | None = None,
        weight_kg: float | None = None,
    ) -> dict:
        cleaned_name = name.strip()
        normalized_email = email.strip().lower()
        provided_password = password

        if not cleaned_name:
            raise SmartFitError(
                message="Name is required.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_NAME",
            )

        if not normalized_email or not _EMAIL_PATTERN.match(normalized_email):
            raise SmartFitError(
                message="A valid email is required.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_EMAIL",
            )

        self._validate_password_strength(provided_password)

        if height_cm is not None and height_cm <= 0:
            raise SmartFitError(
                message="Height must be greater than 0.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_HEIGHT",
            )

        if weight_kg is not None and weight_kg <= 0:
            raise SmartFitError(
                message="Weight must be greater than 0.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_WEIGHT",
            )

        user_id = f"user_{uuid4().hex[:12]}"
        created_at = self._utc_now()
        password_hash = self._hash_password(provided_password)

        with self._lock:
            with self._connect() as connection:
                existing = connection.execute(
                    "SELECT id FROM auth_users WHERE email = ?",
                    (normalized_email,),
                ).fetchone()

                if existing is not None:
                    raise SmartFitError(
                        message="An account already exists with this email.",
                        status_code=status.HTTP_409_CONFLICT,
                        error_code="AUTH_EMAIL_EXISTS",
                    )

                connection.execute(
                    """
                    INSERT INTO auth_users (
                        id,
                        name,
                        email,
                        password_hash,
                        height_cm,
                        weight_kg,
                        created_at,
                        last_login_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        cleaned_name,
                        normalized_email,
                        password_hash,
                        height_cm,
                        weight_kg,
                        created_at,
                        created_at,
                    ),
                )
                connection.commit()

        return self.get_user(user_id)

    def authenticate(self, email: str, password: str) -> dict:
        normalized_email = email.strip().lower()
        provided_password = password

        if not normalized_email or not provided_password:
            raise SmartFitError(
                message="Email and password are required.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="MISSING_CREDENTIALS",
            )

        now = self._utc_now_dt()

        with self._lock:
            with self._connect() as connection:
                self._ensure_not_locked(connection, normalized_email, now)

                row = connection.execute(
                    "SELECT * FROM auth_users WHERE email = ?",
                    (normalized_email,),
                ).fetchone()

                password_matches = False
                if row is not None:
                    password_matches = self._verify_password(
                        plaintext_password=provided_password,
                        stored_hash=row["password_hash"],
                    )
                    if not password_matches:
                        # Backward compatibility for accounts created when UI/password handling trimmed input.
                        trimmed_password = provided_password.strip()
                        if trimmed_password != provided_password:
                            password_matches = self._verify_password(
                                plaintext_password=trimmed_password,
                                stored_hash=row["password_hash"],
                            )

                if row is None or not password_matches:
                    locked_until = self._record_failed_attempt(
                        connection=connection,
                        email=normalized_email,
                        now=now,
                    )
                    connection.commit()

                    if locked_until is not None:
                        retry_minutes = max(
                            1,
                            int((locked_until - now).total_seconds() // 60) + 1,
                        )
                        raise SmartFitError(
                            message=f"Too many failed login attempts. Try again in {retry_minutes} minute(s).",
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            error_code="AUTH_LOCKED",
                        )

                    raise SmartFitError(
                        message="Invalid email or password.",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        error_code="INVALID_CREDENTIALS",
                    )

                last_login_at = self._utc_now()
                connection.execute(
                    "UPDATE auth_users SET last_login_at = ? WHERE id = ?",
                    (last_login_at, row["id"]),
                )
                connection.execute(
                    "DELETE FROM auth_login_attempts WHERE email = ?",
                    (normalized_email,),
                )
                connection.commit()

        return self.get_user(row["id"])

    def create_session(self, user_id: str) -> dict:
        user = self.get_user(user_id)
        now = self._utc_now_dt()
        refresh_expires = now + timedelta(days=self.refresh_token_days)
        access_expires = now + timedelta(minutes=self.access_token_minutes)

        refresh_token = secrets.token_urlsafe(48)
        refresh_token_hash = self._hash_refresh_token(refresh_token)

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO auth_sessions (
                        id,
                        user_id,
                        refresh_token_hash,
                        created_at,
                        last_used_at,
                        expires_at,
                        revoked_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"session_{uuid4().hex[:16]}",
                        user_id,
                        refresh_token_hash,
                        now.isoformat(),
                        now.isoformat(),
                        refresh_expires.isoformat(),
                        None,
                    ),
                )
                connection.commit()

        access_token = self._encode_access_token(user_id=user_id, expires_at=access_expires)
        return {
            "user": user,
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "access_expires_at": access_expires.isoformat(),
                "refresh_expires_at": refresh_expires.isoformat(),
            },
        }

    def refresh_session(self, refresh_token: str) -> dict:
        cleaned_refresh_token = refresh_token.strip()
        if not cleaned_refresh_token:
            raise SmartFitError(
                message="Refresh token is required.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="MISSING_REFRESH_TOKEN",
            )

        now = self._utc_now_dt()
        refresh_hash = self._hash_refresh_token(cleaned_refresh_token)
        new_refresh_token = secrets.token_urlsafe(48)
        new_refresh_hash = self._hash_refresh_token(new_refresh_token)

        with self._lock:
            with self._connect() as connection:
                session_row = connection.execute(
                    """
                    SELECT id, user_id, expires_at, revoked_at
                    FROM auth_sessions
                    WHERE refresh_token_hash = ?
                    """,
                    (refresh_hash,),
                ).fetchone()

                if session_row is None:
                    raise SmartFitError(
                        message="Invalid refresh token.",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        error_code="INVALID_REFRESH_TOKEN",
                    )

                if session_row["revoked_at"] is not None:
                    raise SmartFitError(
                        message="Refresh token has been revoked.",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        error_code="REVOKED_REFRESH_TOKEN",
                    )

                expires_at = self._parse_datetime(session_row["expires_at"])
                if expires_at <= now:
                    connection.execute(
                        "UPDATE auth_sessions SET revoked_at = ? WHERE id = ?",
                        (now.isoformat(), session_row["id"]),
                    )
                    connection.commit()
                    raise SmartFitError(
                        message="Refresh token expired. Please sign in again.",
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        error_code="EXPIRED_REFRESH_TOKEN",
                    )

                refreshed_expires = now + timedelta(days=self.refresh_token_days)
                connection.execute(
                    """
                    UPDATE auth_sessions
                    SET refresh_token_hash = ?,
                        last_used_at = ?,
                        expires_at = ?
                    WHERE id = ?
                    """,
                    (
                        new_refresh_hash,
                        now.isoformat(),
                        refreshed_expires.isoformat(),
                        session_row["id"],
                    ),
                )
                connection.commit()

                user = self.get_user(session_row["user_id"])

        access_expires = now + timedelta(minutes=self.access_token_minutes)
        access_token = self._encode_access_token(user_id=user["id"], expires_at=access_expires)

        return {
            "user": user,
            "tokens": {
                "access_token": access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "access_expires_at": access_expires.isoformat(),
                "refresh_expires_at": refreshed_expires.isoformat(),
            },
        }

    def revoke_session(self, refresh_token: str) -> bool:
        cleaned_refresh_token = refresh_token.strip()
        if not cleaned_refresh_token:
            return False

        now = self._utc_now()
        refresh_hash = self._hash_refresh_token(cleaned_refresh_token)

        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    UPDATE auth_sessions
                    SET revoked_at = ?
                    WHERE refresh_token_hash = ? AND revoked_at IS NULL
                    """,
                    (now, refresh_hash),
                )
                connection.commit()

        return cursor.rowcount > 0

    def get_user_from_access_token(self, access_token: str) -> dict:
        user_id = self._decode_access_token(access_token)
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    id,
                    name,
                    email,
                    height_cm,
                    weight_kg,
                    created_at,
                    last_login_at
                FROM auth_users
                WHERE id = ?
                """,
                (user_id,),
            ).fetchone()

        if row is None:
            raise SmartFitError(
                message="User not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="AUTH_USER_NOT_FOUND",
            )

        return dict(row)

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    height_cm REAL,
                    weight_kg REAL,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_auth_users_email
                ON auth_users(email)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    refresh_token_hash TEXT NOT NULL UNIQUE,
                    created_at TEXT NOT NULL,
                    last_used_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    revoked_at TEXT,
                    FOREIGN KEY(user_id) REFERENCES auth_users(id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id
                ON auth_sessions(user_id)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auth_login_attempts (
                    email TEXT PRIMARY KEY,
                    failed_attempts INTEGER NOT NULL,
                    last_failed_at TEXT NOT NULL,
                    locked_until TEXT
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _utc_now_dt() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_datetime(raw_value: str) -> datetime:
        parsed = datetime.fromisoformat(raw_value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _hash_password(plaintext_password: str) -> str:
        salt = secrets.token_hex(16)
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            plaintext_password.encode("utf-8"),
            salt.encode("utf-8"),
            _PBKDF2_ITERATIONS,
        )
        return f"{_HASH_SCHEME}${_PBKDF2_ITERATIONS}${salt}${derived_key.hex()}"

    @staticmethod
    def _verify_password(plaintext_password: str, stored_hash: str) -> bool:
        try:
            scheme, rounds, salt, digest = stored_hash.split("$", 3)
            if scheme != _HASH_SCHEME:
                return False

            derived_key = hashlib.pbkdf2_hmac(
                "sha256",
                plaintext_password.encode("utf-8"),
                salt.encode("utf-8"),
                int(rounds),
            )
            return hmac.compare_digest(derived_key.hex(), digest)
        except (TypeError, ValueError):
            return False

    def _validate_password_strength(self, password: str) -> None:
        has_required_sets = all(
            [
                _PASSWORD_HAS_LOWER.search(password),
                _PASSWORD_HAS_UPPER.search(password),
                _PASSWORD_HAS_DIGIT.search(password),
                _PASSWORD_HAS_SYMBOL.search(password),
            ]
        )
        if len(password) < 8 or not has_required_sets:
            raise SmartFitError(
                message=(
                    "Password must be at least 8 characters and include upper, lower, number, and symbol."
                ),
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_PASSWORD_POLICY",
            )

    def _ensure_not_locked(self, connection: sqlite3.Connection, email: str, now: datetime) -> None:
        row = connection.execute(
            "SELECT locked_until FROM auth_login_attempts WHERE email = ?",
            (email,),
        ).fetchone()

        if row is None or row["locked_until"] is None:
            return

        locked_until = self._parse_datetime(row["locked_until"])
        if locked_until <= now:
            connection.execute("DELETE FROM auth_login_attempts WHERE email = ?", (email,))
            return

        retry_minutes = max(1, int((locked_until - now).total_seconds() // 60) + 1)
        raise SmartFitError(
            message=f"Too many failed login attempts. Try again in {retry_minutes} minute(s).",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="AUTH_LOCKED",
        )

    def _record_failed_attempt(
        self,
        connection: sqlite3.Connection,
        email: str,
        now: datetime,
    ) -> datetime | None:
        existing = connection.execute(
            """
            SELECT failed_attempts, last_failed_at, locked_until
            FROM auth_login_attempts
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

        attempts = 1
        if existing is not None:
            last_failed = self._parse_datetime(existing["last_failed_at"])
            within_window = now - last_failed <= timedelta(minutes=self.attempt_window_minutes)
            attempts = (existing["failed_attempts"] + 1) if within_window else 1

        locked_until: datetime | None = None
        if attempts >= self.max_failed_attempts:
            locked_until = now + timedelta(minutes=self.lockout_minutes)

        connection.execute(
            """
            INSERT INTO auth_login_attempts (email, failed_attempts, last_failed_at, locked_until)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                failed_attempts=excluded.failed_attempts,
                last_failed_at=excluded.last_failed_at,
                locked_until=excluded.locked_until
            """,
            (
                email,
                attempts,
                now.isoformat(),
                locked_until.isoformat() if locked_until is not None else None,
            ),
        )

        return locked_until

    @staticmethod
    def _hash_refresh_token(refresh_token: str) -> str:
        return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _b64url_encode(payload: bytes) -> str:
        return base64.urlsafe_b64encode(payload).decode("utf-8").rstrip("=")

    @staticmethod
    def _b64url_decode(payload: str) -> bytes:
        padding = "=" * ((4 - len(payload) % 4) % 4)
        return base64.urlsafe_b64decode((payload + padding).encode("utf-8"))

    def _encode_access_token(self, user_id: str, expires_at: datetime) -> str:
        payload = {
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(expires_at.timestamp()),
            "jti": uuid4().hex,
        }
        encoded_payload = self._b64url_encode(
            json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        )
        signature = hmac.new(
            self.access_token_secret.encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        encoded_signature = self._b64url_encode(signature)
        return f"{encoded_payload}.{encoded_signature}"

    def _decode_access_token(self, access_token: str) -> str:
        token = access_token.strip()
        if not token:
            raise SmartFitError(
                message="Access token is required.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="MISSING_ACCESS_TOKEN",
            )

        try:
            payload_part, signature_part = token.split(".", 1)
        except ValueError as exc:
            raise SmartFitError(
                message="Invalid access token format.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_ACCESS_TOKEN",
            ) from exc

        expected_signature = hmac.new(
            self.access_token_secret.encode("utf-8"),
            payload_part.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_signature_part = self._b64url_encode(expected_signature)

        if not hmac.compare_digest(expected_signature_part, signature_part):
            raise SmartFitError(
                message="Invalid access token signature.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_ACCESS_TOKEN",
            )

        try:
            payload = json.loads(self._b64url_decode(payload_part).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            raise SmartFitError(
                message="Invalid access token payload.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_ACCESS_TOKEN",
            ) from exc

        expires_at = int(payload.get("exp") or 0)
        if expires_at <= int(time.time()):
            raise SmartFitError(
                message="Access token expired.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="EXPIRED_ACCESS_TOKEN",
            )

        user_id = str(payload.get("sub") or "").strip()
        if not user_id:
            raise SmartFitError(
                message="Invalid access token subject.",
                status_code=status.HTTP_401_UNAUTHORIZED,
                error_code="INVALID_ACCESS_TOKEN",
            )

        return user_id
