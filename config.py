"""
Configuration management for Pomodoro Reminder using SQLite storage.
"""

import sqlite3
import os
from datetime import datetime

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pomodoro_reminder")
DB_FILE = os.path.join(CONFIG_DIR, "config.db")

DEFAULT_CONFIG = {
    "work_minutes": "30",
    "break_minutes": "5",
    "alarm_sound_path": "",  # Empty means use default beep
    "show_widget": "1",      # "0" = False, "1" = True
}

# Type mapping for converting between SQLite text and Python types
TYPE_MAP = {
    "work_minutes": int,
    "break_minutes": int,
    "alarm_sound_path": str,
    "show_widget": lambda v: v == "1" or v is True,
}


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection, creating the DB and table if needed."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productivity_log (
            log_date           TEXT PRIMARY KEY,
            work_seconds       INTEGER NOT NULL DEFAULT 0,
            completed_sessions INTEGER NOT NULL DEFAULT 0,
            updated_at         TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def load_config() -> dict:
    """Load configuration from SQLite, returning defaults for missing keys."""
    conn = _get_connection()
    try:
        cursor = conn.execute("SELECT key, value FROM config")
        rows = {row[0]: row[1] for row in cursor.fetchall()}

        config = {}
        for key, default_val in DEFAULT_CONFIG.items():
            raw = rows.get(key, default_val)
            converter = TYPE_MAP.get(key, str)
            try:
                config[key] = converter(raw)
            except (ValueError, TypeError):
                config[key] = converter(default_val)
        return config
    finally:
        conn.close()


def save_config(config: dict):
    """Save configuration to SQLite using upsert."""
    conn = _get_connection()
    try:
        for key, value in config.items():
            # Convert Python types to string for storage
            if isinstance(value, bool):
                db_value = "1" if value else "0"
            else:
                db_value = str(value)

            conn.execute(
                """
                INSERT INTO config (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, db_value)
            )
        conn.commit()
    finally:
        conn.close()


def add_productivity_log(log_date: str, work_seconds: int = 0, completed_sessions: int = 0):
    """Add daily productivity totals for the given ISO date."""
    if work_seconds <= 0 and completed_sessions <= 0:
        return

    conn = _get_connection()
    try:
        conn.execute(
            """
            INSERT INTO productivity_log (
                log_date, work_seconds, completed_sessions, updated_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(log_date) DO UPDATE SET
                work_seconds = work_seconds + excluded.work_seconds,
                completed_sessions = completed_sessions + excluded.completed_sessions,
                updated_at = excluded.updated_at
            """,
            (
                log_date,
                max(0, int(work_seconds)),
                max(0, int(completed_sessions)),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_productivity_entry(log_date: str) -> dict:
    """Return productivity totals for a single date."""
    conn = _get_connection()
    try:
        row = conn.execute(
            """
            SELECT log_date, work_seconds, completed_sessions
            FROM productivity_log
            WHERE log_date = ?
            """,
            (log_date,),
        ).fetchone()
        if row is None:
            return {
                "log_date": log_date,
                "work_seconds": 0,
                "completed_sessions": 0,
            }
        return {
            "log_date": row[0],
            "work_seconds": int(row[1]),
            "completed_sessions": int(row[2]),
        }
    finally:
        conn.close()


def get_productivity_log(limit: int = 7) -> list[dict]:
    """Return recent daily productivity totals, newest first."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            """
            SELECT log_date, work_seconds, completed_sessions
            FROM productivity_log
            ORDER BY log_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {
                "log_date": row[0],
                "work_seconds": int(row[1]),
                "completed_sessions": int(row[2]),
            }
            for row in rows
        ]
    finally:
        conn.close()

