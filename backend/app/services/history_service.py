from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .database_service import DatabaseService


class HistoryService:
    _legacy_storage_path: Path | None = None
    _max_records = 50
    _configured = False

    @classmethod
    def configure(cls, config: dict) -> None:
        DatabaseService.configure(config)

        project_root = Path(__file__).resolve().parents[3]
        configured_path = str(config.get("HISTORY_STORAGE_PATH", "")).strip()
        path = Path(configured_path) if configured_path else Path("local_assets/backend/history/analysis_history.json")
        if not path.is_absolute():
            path = (project_root / path).resolve()

        max_records = int(config.get("HISTORY_MAX_RECORDS", 50))
        if cls._configured and cls._legacy_storage_path == path and cls._max_records == max_records:
            return

        cls._legacy_storage_path = path
        cls._max_records = max_records
        cls._migrate_legacy_history()
        cls._trim_records()
        cls._configured = True

    @classmethod
    def add_record(cls, record: dict, history_context: dict | None = None) -> dict:
        entry = deepcopy(record)
        entry["created_at"] = datetime.now(timezone.utc).isoformat()
        context = history_context or {}
        entry["member_account"] = str(context.get("member_account", "")).strip()
        entry["member_name"] = str(context.get("member_name", "")).strip()
        entry["viewer_role"] = str(context.get("viewer_role", "visitor")).strip() or "visitor"
        entry["journal_entry_id"] = ""

        with DatabaseService.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO history_records(
                    member_account,
                    member_name,
                    viewer_role,
                    created_at,
                    payload_json,
                    journal_entry_id
                )
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["member_account"],
                    entry["member_name"],
                    entry["viewer_role"],
                    entry["created_at"],
                    json.dumps(entry, ensure_ascii=False),
                    "",
                ),
            )
            history_record_id = int(cursor.lastrowid or 0)
            entry["history_record_id"] = history_record_id
            conn.execute(
                "UPDATE history_records SET payload_json = ? WHERE id = ?",
                (json.dumps(entry, ensure_ascii=False), history_record_id),
            )
            conn.commit()

        cls._trim_records()
        return entry

    @classmethod
    def list_records(cls, member_account: str = "", include_all: bool = False) -> list[dict]:
        query = "SELECT id, journal_entry_id, payload_json FROM history_records"
        params: list[Any] = []

        if not include_all:
            query += " WHERE (? = '' OR member_account = ?)"
            normalized = str(member_account or "").strip()
            params.extend([normalized, normalized])

        query += " ORDER BY created_at DESC, id DESC"

        with DatabaseService.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        items: list[dict] = []
        for row in rows:
            payload = cls._decode_payload(row["payload_json"])
            if not isinstance(payload, dict):
                continue
            payload["history_record_id"] = int(row["id"])
            payload["journal_entry_id"] = str(row["journal_entry_id"] or payload.get("journal_entry_id", ""))
            payload["added_to_journal"] = bool(payload["journal_entry_id"])
            items.append(payload)
        return items

    @classmethod
    def attach_journal_entry(cls, history_record_id: int | str | None, journal_entry_id: str) -> None:
        target_id = cls._normalize_history_record_id(history_record_id)
        journal_id = str(journal_entry_id or "").strip()
        if target_id is None or not journal_id:
            return

        with DatabaseService.connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM history_records WHERE id = ?",
                (target_id,),
            ).fetchone()
            if row is None:
                return

            payload = cls._decode_payload(row["payload_json"])
            if not isinstance(payload, dict):
                payload = {}

            payload["history_record_id"] = target_id
            payload["journal_entry_id"] = journal_id
            payload["added_to_journal"] = True

            conn.execute(
                """
                UPDATE history_records
                SET journal_entry_id = ?, payload_json = ?
                WHERE id = ?
                """,
                (journal_id, json.dumps(payload, ensure_ascii=False), target_id),
            )
            conn.commit()

    @classmethod
    def detach_journal_entry(cls, history_record_id: int | str | None, journal_entry_id: str = "") -> None:
        target_id = cls._normalize_history_record_id(history_record_id)
        if target_id is None:
            return

        journal_id = str(journal_entry_id or "").strip()

        with DatabaseService.connect() as conn:
            if journal_id:
                row = conn.execute(
                    """
                    SELECT payload_json
                    FROM history_records
                    WHERE id = ? AND journal_entry_id = ?
                    """,
                    (target_id, journal_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT payload_json FROM history_records WHERE id = ?",
                    (target_id,),
                ).fetchone()

            if row is None:
                return

            payload = cls._decode_payload(row["payload_json"])
            if not isinstance(payload, dict):
                payload = {}

            payload["history_record_id"] = target_id
            payload["journal_entry_id"] = ""
            payload["added_to_journal"] = False

            conn.execute(
                """
                UPDATE history_records
                SET journal_entry_id = '', payload_json = ?
                WHERE id = ?
                """,
                (json.dumps(payload, ensure_ascii=False), target_id),
            )
            conn.commit()

    @classmethod
    def _migrate_legacy_history(cls) -> None:
        if DatabaseService.get_meta("history_legacy_import_v1", "") == "done":
            return

        if cls._legacy_storage_path is None or not cls._legacy_storage_path.exists():
            DatabaseService.set_meta("history_legacy_import_v1", "done")
            return

        try:
            raw = json.loads(cls._legacy_storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            DatabaseService.set_meta("history_legacy_import_v1", "done")
            return

        if not isinstance(raw, list):
            DatabaseService.set_meta("history_legacy_import_v1", "done")
            return

        with DatabaseService.connect() as conn:
            for item in raw:
                if not isinstance(item, dict):
                    continue

                created_at = str(item.get("created_at") or datetime.now(timezone.utc).isoformat())
                journal_entry_id = str(item.get("journal_entry_id", "")).strip()
                payload = deepcopy(item)
                payload["journal_entry_id"] = journal_entry_id
                payload["added_to_journal"] = bool(journal_entry_id)

                conn.execute(
                    """
                    INSERT INTO history_records(
                        member_account,
                        member_name,
                        viewer_role,
                        created_at,
                        payload_json,
                        journal_entry_id
                    )
                    VALUES(?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(item.get("member_account", "")).strip(),
                        str(item.get("member_name", "")).strip(),
                        str(item.get("viewer_role", "visitor")).strip() or "visitor",
                        created_at,
                        json.dumps(payload, ensure_ascii=False),
                        journal_entry_id,
                    ),
                )
            conn.commit()

        with DatabaseService.connect() as conn:
            rows = conn.execute("SELECT id, payload_json FROM history_records").fetchall()
            for row in rows:
                payload = cls._decode_payload(row["payload_json"])
                if not isinstance(payload, dict):
                    continue
                payload["history_record_id"] = int(row["id"])
                conn.execute(
                    "UPDATE history_records SET payload_json = ? WHERE id = ?",
                    (json.dumps(payload, ensure_ascii=False), int(row["id"])),
                )
            conn.commit()

        cls._trim_records()
        DatabaseService.set_meta("history_legacy_import_v1", "done")

    @classmethod
    def _trim_records(cls) -> None:
        with DatabaseService.connect() as conn:
            conn.execute(
                """
                DELETE FROM history_records
                WHERE id NOT IN (
                    SELECT id
                    FROM history_records
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                )
                """,
                (cls._max_records,),
            )
            conn.commit()

    @staticmethod
    def _decode_payload(raw_payload: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(raw_payload)
        except (TypeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _normalize_history_record_id(value: int | str | None) -> int | None:
        try:
            normalized = int(value or 0)
        except (TypeError, ValueError):
            return None
        return normalized if normalized > 0 else None
