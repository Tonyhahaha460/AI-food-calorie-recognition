from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class DatabaseService:
    _db_path: Path | None = None
    _configured = False

    @classmethod
    def configure(cls, config: dict[str, Any]) -> None:
        project_root = Path(__file__).resolve().parents[3]
        configured_path = str(config.get("DATABASE_PATH", "")).strip()
        path = Path(configured_path) if configured_path else Path("local_assets/backend/database/app.db")
        if not path.is_absolute():
            path = (project_root / path).resolve()

        if cls._configured and cls._db_path == path:
            return

        cls._db_path = path
        cls._db_path.parent.mkdir(parents=True, exist_ok=True)
        with cls.connect() as conn:
            cls._create_schema(conn)
        cls._configured = True

    @classmethod
    def connect(cls) -> sqlite3.Connection:
        if cls._db_path is None:
            raise RuntimeError("DatabaseService is not configured.")

        connection = sqlite3.connect(str(cls._db_path))
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @classmethod
    def get_meta(cls, key: str, default: str = "") -> str:
        with cls.connect() as conn:
            row = conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return str(row["value"] or default)

    @classmethod
    def set_meta(cls, key: str, value: str) -> None:
        with cls.connect() as conn:
            conn.execute(
                """
                INSERT INTO metadata(key, value)
                VALUES(?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            conn.commit()

    @staticmethod
    def _create_schema(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS members (
                account TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                gender TEXT NOT NULL,
                height_cm REAL NOT NULL,
                weight_kg REAL NOT NULL,
                age INTEGER NOT NULL,
                activity_level TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                member_account TEXT NOT NULL,
                food_name TEXT NOT NULL,
                portion_label TEXT NOT NULL,
                image_preview TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL,
                date_key TEXT NOT NULL,
                calories REAL NOT NULL DEFAULT 0,
                protein REAL NOT NULL DEFAULT 0,
                fat REAL NOT NULL DEFAULT 0,
                carbs REAL NOT NULL DEFAULT 0,
                history_record_id INTEGER,
                FOREIGN KEY(member_account) REFERENCES members(account) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_journal_member_date
            ON journal_entries(member_account, date_key, created_at DESC);

            CREATE TABLE IF NOT EXISTS history_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_account TEXT NOT NULL DEFAULT '',
                member_name TEXT NOT NULL DEFAULT '',
                viewer_role TEXT NOT NULL DEFAULT 'visitor',
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                journal_entry_id TEXT NOT NULL DEFAULT ''
            );

            CREATE INDEX IF NOT EXISTS idx_history_member_created
            ON history_records(member_account, created_at DESC);

            """
        )
        DatabaseService._ensure_column(conn, "journal_entries", "history_record_id", "INTEGER")
        DatabaseService._ensure_column(conn, "history_records", "journal_entry_id", "TEXT NOT NULL DEFAULT ''")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_journal_history_record ON journal_entries(history_record_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_journal_entry ON history_records(journal_entry_id)"
        )
        conn.commit()

    @staticmethod
    def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}
        if column in existing:
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
