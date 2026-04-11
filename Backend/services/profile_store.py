from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import status

from utils.exceptions import SmartFitError


class ProfileStoreService:
    """SQLite-backed storage for profiles, scan history, and trend exports."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def create_profile(self, name: str) -> dict:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise SmartFitError(
                message="Profile name cannot be empty.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_PROFILE_NAME",
            )

        profile_id = f"profile_{uuid4().hex[:12]}"
        now = self._utc_now()

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO profiles (id, name, created_at) VALUES (?, ?, ?)",
                    (profile_id, cleaned_name, now),
                )
                connection.commit()

        return self.get_profile(profile_id)

    def list_profiles(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.created_at,
                    COUNT(s.id) AS scan_count,
                    MAX(s.created_at) AS last_scan_at
                FROM profiles p
                LEFT JOIN scans s ON p.id = s.profile_id
                GROUP BY p.id, p.name, p.created_at
                ORDER BY p.created_at DESC
                """
            ).fetchall()

        return [dict(row) for row in rows]

    def get_profile(self, profile_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT
                    p.id,
                    p.name,
                    p.created_at,
                    COUNT(s.id) AS scan_count,
                    MAX(s.created_at) AS last_scan_at
                FROM profiles p
                LEFT JOIN scans s ON p.id = s.profile_id
                WHERE p.id = ?
                GROUP BY p.id, p.name, p.created_at
                """,
                (profile_id,),
            ).fetchone()

        if row is None:
            raise SmartFitError(
                message="Profile not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="PROFILE_NOT_FOUND",
            )

        return dict(row)

    def update_profile(self, profile_id: str, name: str) -> dict:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise SmartFitError(
                message="Profile name cannot be empty.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                error_code="INVALID_PROFILE_NAME",
            )

        self.get_profile(profile_id)

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    "UPDATE profiles SET name = ? WHERE id = ?",
                    (cleaned_name, profile_id),
                )
                connection.commit()

        return self.get_profile(profile_id)

    def save_scan(self, profile_id: str, analysis_payload: dict) -> str:
        self.get_profile(profile_id)

        scan_id = f"scan_{uuid4().hex[:14]}"
        now = self._utc_now()

        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO scans (
                        id,
                        profile_id,
                        created_at,
                        fit_preference,
                        unit_system,
                        predicted_size,
                        confidence,
                        measurements_json,
                        brand_mapping_json,
                        recommendations_json,
                        explainability_json,
                        return_risk_json,
                        capture_quality_json,
                        privacy_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        scan_id,
                        profile_id,
                        now,
                        analysis_payload.get("fit_preference", "regular"),
                        analysis_payload.get("measurement_unit", "cm"),
                        analysis_payload.get("predicted_size", "M"),
                        float(analysis_payload.get("confidence", 0.0)),
                        json.dumps(analysis_payload.get("measurements", {})),
                        json.dumps(analysis_payload.get("brand_mapping", {})),
                        json.dumps(analysis_payload.get("recommendations", [])),
                        json.dumps(analysis_payload.get("explainability", {})),
                        json.dumps(analysis_payload.get("return_risk", {})),
                        json.dumps(analysis_payload.get("capture_quality", {})),
                        json.dumps(analysis_payload.get("privacy", {})),
                    ),
                )
                connection.commit()

        return scan_id

    def list_history(self, profile_id: str, limit: int = 100) -> list[dict]:
        self.get_profile(profile_id)

        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM scans
                WHERE profile_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (profile_id, max(1, limit)),
            ).fetchall()

        return [self._scan_row_to_dict(row) for row in rows]

    def get_scan(self, profile_id: str, scan_id: str) -> dict:
        self.get_profile(profile_id)

        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM scans WHERE profile_id = ? AND id = ?",
                (profile_id, scan_id),
            ).fetchone()

        if row is None:
            raise SmartFitError(
                message="Scan not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SCAN_NOT_FOUND",
            )

        return self._scan_row_to_dict(row)

    def trends(self, profile_id: str) -> dict:
        history = list(reversed(self.list_history(profile_id, limit=500)))

        points: list[dict] = []
        for record in history:
            measurements = record.get("measurements", {})
            points.append(
                {
                    "analyzed_at": record.get("analyzed_at"),
                    "chest": measurements.get("chest"),
                    "waist": measurements.get("waist"),
                    "shoulder": measurements.get("shoulder"),
                }
            )

        deltas = {"chest": 0.0, "waist": 0.0, "shoulder": 0.0}
        if len(points) >= 2:
            first = points[0]
            last = points[-1]
            for key in deltas:
                first_value = float(first.get(key) or 0.0)
                last_value = float(last.get(key) or 0.0)
                deltas[key] = round(last_value - first_value, 2)

        return {
            "profile_id": profile_id,
            "points": points,
            "deltas": deltas,
        }

    def export_profile(self, profile_id: str) -> dict:
        return {
            "profile": self.get_profile(profile_id),
            "history": self.list_history(profile_id, limit=1000),
            "trends": self.trends(profile_id),
        }

    def delete_profile(self, profile_id: str) -> None:
        self.get_profile(profile_id)

        with self._lock:
            with self._connect() as connection:
                connection.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
                connection.commit()

    def delete_scan(self, profile_id: str, scan_id: str) -> None:
        self.get_profile(profile_id)

        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM scans WHERE profile_id = ? AND id = ?",
                    (profile_id, scan_id),
                )
                connection.commit()

        if cursor.rowcount == 0:
            raise SmartFitError(
                message="Scan not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SCAN_NOT_FOUND",
            )

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    fit_preference TEXT NOT NULL,
                    unit_system TEXT NOT NULL,
                    predicted_size TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    measurements_json TEXT NOT NULL,
                    brand_mapping_json TEXT NOT NULL,
                    recommendations_json TEXT NOT NULL,
                    explainability_json TEXT NOT NULL,
                    return_risk_json TEXT NOT NULL,
                    capture_quality_json TEXT NOT NULL,
                    privacy_json TEXT NOT NULL,
                    FOREIGN KEY(profile_id) REFERENCES profiles(id) ON DELETE CASCADE
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
    def _scan_row_to_dict(row: sqlite3.Row) -> dict:
        return {
            "scan_id": row["id"],
            "profile_id": row["profile_id"],
            "analyzed_at": row["created_at"],
            "fit_preference": row["fit_preference"],
            "measurement_unit": row["unit_system"],
            "predicted_size": row["predicted_size"],
            "confidence": row["confidence"],
            "measurements": json.loads(row["measurements_json"]),
            "brand_mapping": json.loads(row["brand_mapping_json"]),
            "recommendations": json.loads(row["recommendations_json"]),
            "explainability": json.loads(row["explainability_json"]),
            "return_risk": json.loads(row["return_risk_json"]),
            "capture_quality": json.loads(row["capture_quality_json"]),
            "privacy": json.loads(row["privacy_json"]),
        }

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()
