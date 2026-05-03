"""
Configuration management for Pomodoro Reminder using SQLite storage.
"""

import sqlite3
import os
import sys

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".pomodoro_reminder")
DB_FILE = os.path.join(CONFIG_DIR, "config.db")

DEFAULT_CONFIG = {
    "work_minutes": "30",
    "break_minutes": "5",
    "alarm_sound_path": "",  # Empty means use default beep
    "run_at_startup": "0",   # "0" = False, "1" = True
}

# Type mapping for converting between SQLite text and Python types
TYPE_MAP = {
    "work_minutes": int,
    "break_minutes": int,
    "alarm_sound_path": str,
    "run_at_startup": lambda v: v == "1" or v is True,
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



def _get_app_path() -> str:
    """Get the path to the running application (exe or script)."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return f'"{sys.executable}" "{os.path.join(script_dir, "main.py")}"'


def _open_run_key():
    """Open the Windows Run registry key. Returns (key, success)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        return key
    except Exception:
        return None


def set_run_at_startup(enabled: bool):
    """Enable or disable run at Windows startup via registry."""
    try:
        import winreg
    except ImportError:
        return

    key = _open_run_key()
    if key is None:
        return

    try:
        if enabled:
            app_path = _get_app_path()
            winreg.SetValueEx(key, "PomodoroReminder", 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, "PomodoroReminder")
            except FileNotFoundError:
                pass
    except Exception as e:
        print(f"Startup registry update failed: {e}")
    finally:
        winreg.CloseKey(key)
