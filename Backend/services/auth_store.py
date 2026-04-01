from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import status

from utils.exceptions import SmartFitError

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PBKDF2_ITERATIONS = 210000
_HASH_SCHEME = "pbkdf2_sha256"


class AuthStoreService:
    """SQLite-backed storage for SmartFit authentication users."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
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
        cleaned_password = password.strip()

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

        if len(cleaned_password) < 6:
            raise SmartFitError(
                message="Password must be at least 6 characters.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_PASSWORD",
            )

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
        password_hash = self._hash_password(cleaned_password)

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
        cleaned_password = password.strip()

        if not normalized_email or not cleaned_password:
            raise SmartFitError(
                message="Email and password are required.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="MISSING_CREDENTIALS",
            )

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM auth_users WHERE email = ?",
                    (normalized_email,),
                ).fetchone()

                if row is None or not self._verify_password(
                    plaintext_password=cleaned_password,
                    stored_hash=row["password_hash"],
                ):
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
                connection.commit()

        return self.get_user(row["id"])

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
