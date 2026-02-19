"""SQLite persistence layer for EcoScan AI.

This module is intentionally framework-agnostic so both FastAPI and scripts can reuse it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent / "ecoscan.db"


def get_connection() -> sqlite3.Connection:
    """Create a SQLite connection with dictionary-like rows."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create and migrate the scans table for MVP analytics needs."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY,
                product_name TEXT,
                barcode TEXT,
                city TEXT,
                impact_score TEXT,
                disposal_type TEXT,
                co2_estimate REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # Lightweight migration to support existing local DB files created by older versions.
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(scans)").fetchall()
        }
        if "co2_estimate" not in columns:
            connection.execute("ALTER TABLE scans ADD COLUMN co2_estimate REAL DEFAULT 0")

        connection.commit()


def insert_scan(
    product_name: str,
    barcode: str,
    city: str,
    impact_score: str,
    disposal_type: str,
    co2_estimate: float,
) -> int:
    """Insert scan row and return created id."""
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (
                product_name,
                barcode,
                city,
                impact_score,
                disposal_type,
                co2_estimate
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_name, barcode, city, impact_score, disposal_type, co2_estimate),
        )
        connection.commit()
        return int(cursor.lastrowid)


def get_scan_by_id(scan_id: int) -> Optional[Dict]:
    """Fetch one scan row by id."""
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, product_name, barcode, city, impact_score, disposal_type, co2_estimate, timestamp
            FROM scans
            WHERE id = ?
            """,
            (scan_id,),
        ).fetchone()
    return dict(row) if row else None


def get_scan_history(limit: int = 100) -> List[Dict]:
    """Fetch most-recent scans."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, product_name, barcode, city, impact_score, disposal_type, co2_estimate, timestamp
            FROM scans
            ORDER BY timestamp DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_live_environmental_score(days: int = 7) -> int:
    """Compute color-based points for recent scans."""
    mapping = {"Green": 3, "Yellow": 2, "Red": 1}
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT impact_score
            FROM scans
            WHERE timestamp >= datetime('now', ?)
            """,
            (f"-{days} days",),
        ).fetchall()
    return sum(mapping.get(row["impact_score"], 2) for row in rows)


def get_total_scans() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM scans").fetchone()
    return int(row["total"] if row else 0)


def get_total_co2() -> float:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT COALESCE(SUM(co2_estimate), 0) AS total_co2 FROM scans"
        ).fetchone()
    return float(row["total_co2"] if row else 0.0)


def get_weekly_co2_series() -> List[Dict]:
    """Return last 7 days of CO2 totals."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT date(timestamp) AS day, ROUND(COALESCE(SUM(co2_estimate), 0), 2) AS co2
            FROM scans
            WHERE timestamp >= datetime('now', '-6 days')
            GROUP BY date(timestamp)
            ORDER BY day ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_impact_distribution() -> List[Dict]:
    """Return aggregate counts by impact color."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT impact_score, COUNT(*) AS count
            FROM scans
            GROUP BY impact_score
            ORDER BY count DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_trend_line(days: int = 30) -> List[Dict]:
    """Return 30-day trend of daily CO2 and scan volume."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                date(timestamp) AS day,
                ROUND(COALESCE(SUM(co2_estimate), 0), 2) AS co2,
                COUNT(*) AS scans
            FROM scans
            WHERE timestamp >= datetime('now', ?)
            GROUP BY date(timestamp)
            ORDER BY day ASC
            """,
            (f"-{days - 1} days",),
        ).fetchall()
    return [dict(row) for row in rows]


def get_current_streak() -> int:
    """Calculate consecutive day streak ending today."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT DISTINCT date(timestamp) AS day
            FROM scans
            ORDER BY day DESC
            """
        ).fetchall()

    days = [row["day"] for row in rows]
    if not days:
        return 0

    from datetime import date, timedelta

    day_set = set(days)
    cursor = date.today()
    streak = 0

    while cursor.isoformat() in day_set:
        streak += 1
        cursor -= timedelta(days=1)

    return streak


def get_monthly_scans(year: int, month: int) -> List[Dict]:
    """Return scans for the selected month."""
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        next_month = f"{year + 1:04d}-01-01"
    else:
        next_month = f"{year:04d}-{month + 1:02d}-01"

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, product_name, barcode, city, impact_score, disposal_type, co2_estimate, timestamp
            FROM scans
            WHERE timestamp >= ? AND timestamp < ?
            ORDER BY timestamp ASC
            """,
            (start, next_month),
        ).fetchall()
    return [dict(row) for row in rows]

