from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .database_service import DatabaseService
from .history_service import HistoryService


class JournalError(Exception):
    pass


class JournalService:
    _legacy_storage_path: Path | None = None
    _configured = False

    @classmethod
    def configure(cls, config: dict[str, Any]) -> None:
        DatabaseService.configure(config)

        project_root = Path(__file__).resolve().parents[3]
        configured_path = str(config.get("JOURNAL_STORAGE_PATH", "")).strip()
        path = Path(configured_path) if configured_path else Path("local_assets/backend/journal/journal_entries.json")
        if not path.is_absolute():
            path = (project_root / path).resolve()

        if cls._configured and cls._legacy_storage_path == path:
            return

        cls._legacy_storage_path = path
        cls._migrate_legacy_entries()
        cls._export_entries_to_legacy_storage()
        cls._configured = True

    @classmethod
    def list_entries(cls, member_account: str, date_key: str = "") -> list[dict[str, Any]]:
        account = str(member_account or "").strip().lower()
        key = str(date_key or "").strip()
        query = """
            SELECT
                id,
                member_account,
                food_name,
                portion_label,
                image_preview,
                source,
                created_at,
                date_key,
                calories,
                protein,
                fat,
                carbs,
                history_record_id
            FROM journal_entries
            WHERE member_account = ?
        """
        params: list[Any] = [account]
        if key:
            query += " AND date_key = ?"
            params.append(key)
        query += " ORDER BY created_at DESC"

        with DatabaseService.connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return [cls._row_to_entry(row) for row in rows]

    @classmethod
    def create_entry(cls, member_account: str, payload: dict[str, Any]) -> dict[str, Any]:
        account = str(member_account or "").strip().lower()
        if not account:
            raise JournalError("請先登入會員。")

        entry = cls._build_entry(account, payload)
        cls._upsert_entry(entry)
        cls._sync_history_link(None, entry)
        return entry

    @classmethod
    def update_entry(cls, member_account: str, entry_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        account = str(member_account or "").strip().lower()
        target_id = str(entry_id or "").strip()

        existing = cls._find_entry(target_id, account)
        if existing is None:
            raise JournalError("找不到這筆日誌資料。")

        next_created_at = patch.get("created_at") or patch.get("recorded_at") or existing["created_at"]
        timestamp = cls._resolve_timestamp({"created_at": next_created_at})
        updated = {
            **existing,
            **{key: value for key, value in patch.items() if key != "nutrition"},
            "created_at": timestamp.isoformat(),
            "date_key": cls._date_key(timestamp),
            "history_record_id": cls._normalize_history_record_id(
                patch.get("history_record_id", existing.get("history_record_id"))
            ),
            "nutrition": cls._normalize_nutrition({**existing, **patch}),
        }
        updated["food_name"] = str(updated.get("food_name", "")).strip() or "未命名餐點"
        updated["portion_label"] = str(updated.get("portion_label", "")).strip() or "1 份"
        updated["source"] = str(updated.get("source", "")).strip() or "manual"
        updated["image_preview"] = str(updated.get("image_preview", "")).strip()

        cls._upsert_entry(updated)
        cls._sync_history_link(existing.get("history_record_id"), updated)
        return updated

    @classmethod
    def delete_entry(cls, member_account: str, entry_id: str) -> None:
        account = str(member_account or "").strip().lower()
        target_id = str(entry_id or "").strip()
        existing = cls._find_entry(target_id, account)
        if existing is None:
            raise JournalError("找不到這筆日誌資料。")

        with DatabaseService.connect() as conn:
            cursor = conn.execute(
                "DELETE FROM journal_entries WHERE id = ? AND member_account = ?",
                (target_id, account),
            )
            conn.commit()

        if cursor.rowcount == 0:
            raise JournalError("找不到這筆日誌資料。")

        cls._sync_history_unlink(existing)
        cls._export_entries_to_legacy_storage()

    @classmethod
    def _find_entry(cls, entry_id: str, member_account: str) -> dict[str, Any] | None:
        with DatabaseService.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    member_account,
                    food_name,
                    portion_label,
                    image_preview,
                    source,
                    created_at,
                    date_key,
                    calories,
                    protein,
                    fat,
                    carbs,
                    history_record_id
                FROM journal_entries
                WHERE id = ? AND member_account = ?
                """,
                (entry_id, member_account),
            ).fetchone()
        return cls._row_to_entry(row) if row is not None else None

    @classmethod
    def _upsert_entry(cls, entry: dict[str, Any]) -> None:
        with DatabaseService.connect() as conn:
            conn.execute(
                """
                INSERT INTO journal_entries(
                    id,
                    member_account,
                    food_name,
                    portion_label,
                    image_preview,
                    source,
                    created_at,
                    date_key,
                    calories,
                    protein,
                    fat,
                    carbs,
                    history_record_id
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    member_account = excluded.member_account,
                    food_name = excluded.food_name,
                    portion_label = excluded.portion_label,
                    image_preview = excluded.image_preview,
                    source = excluded.source,
                    created_at = excluded.created_at,
                    date_key = excluded.date_key,
                    calories = excluded.calories,
                    protein = excluded.protein,
                    fat = excluded.fat,
                    carbs = excluded.carbs,
                    history_record_id = excluded.history_record_id
                """,
                (
                    entry["id"],
                    entry["member_account"],
                    entry["food_name"],
                    entry["portion_label"],
                    entry["image_preview"],
                    entry["source"],
                    entry["created_at"],
                    entry["date_key"],
                    float(entry["nutrition"]["calories"]),
                    float(entry["nutrition"]["protein"]),
                    float(entry["nutrition"]["fat"]),
                    float(entry["nutrition"]["carbs"]),
                    entry["history_record_id"],
                ),
            )
            conn.commit()
        cls._export_entries_to_legacy_storage()

    @classmethod
    def _build_entry(cls, member_account: str, payload: dict[str, Any]) -> dict[str, Any]:
        timestamp = cls._resolve_timestamp(payload)
        return {
            "id": str(payload.get("id") or uuid4()),
            "member_account": member_account,
            "food_name": str(payload.get("food_name", "")).strip() or "未命名餐點",
            "portion_label": str(payload.get("portion_label", "")).strip() or "1 份",
            "image_preview": str(payload.get("image_preview", "")).strip(),
            "source": str(payload.get("source", "")).strip() or "manual",
            "created_at": timestamp.isoformat(),
            "date_key": cls._date_key(timestamp),
            "history_record_id": cls._normalize_history_record_id(payload.get("history_record_id")),
            "nutrition": cls._normalize_nutrition(payload),
        }

    @staticmethod
    def _row_to_entry(row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "member_account": row["member_account"],
            "food_name": row["food_name"],
            "portion_label": row["portion_label"],
            "image_preview": row["image_preview"],
            "source": row["source"],
            "created_at": row["created_at"],
            "date_key": row["date_key"],
            "history_record_id": int(row["history_record_id"] or 0),
            "nutrition": {
                "calories": float(row["calories"]),
                "protein": float(row["protein"]),
                "fat": float(row["fat"]),
                "carbs": float(row["carbs"]),
            },
        }

    @staticmethod
    def _normalize_nutrition(nutrition: dict[str, Any] | None) -> dict[str, float]:
        data = nutrition if isinstance(nutrition, dict) else {}
        nested = data.get("nutrition") if isinstance(data.get("nutrition"), dict) else {}
        total = data.get("total_nutrition") if isinstance(data.get("total_nutrition"), dict) else {}

        def coerce_float(value: Any) -> float:
            if isinstance(value, str):
                normalized = value.replace(",", "").strip()
                number = ""
                for char in normalized:
                    if char.isdigit() or char in ".-":
                        number += char
                    elif number:
                        break
                value = number
            return float(value or 0)

        def number_for(aliases: tuple[str, ...]) -> float:
            for source in (nested, total, data):
                for key, value in source.items():
                    if str(key).strip().lower() not in aliases:
                        continue
                    try:
                        return coerce_float(value or 0)
                    except (TypeError, ValueError):
                        return 0.0
            return 0.0

        return {
            "calories": number_for(("calories", "calorie", "kcal", "heat", "熱量", "total_calories")),
            "protein": number_for(("protein", "protein_g", "proteins", "蛋白質")),
            "fat": number_for(("fat", "fat_g", "fats", "脂肪")),
            "carbs": number_for(
                ("carbs", "carb", "carbs_g", "carbohydrate", "carbohydrates", "carbohydrate_g", "碳水", "碳水化合物")
            ),
        }

    @staticmethod
    def _normalize_history_record_id(value: Any) -> int | None:
        try:
            normalized = int(value or 0)
        except (TypeError, ValueError):
            return None
        return normalized if normalized > 0 else None

    @staticmethod
    def _resolve_timestamp(payload: dict[str, Any]) -> datetime:
        candidate = payload.get("recorded_at") or payload.get("created_at")
        if not candidate:
            return datetime.now().astimezone()

        if isinstance(candidate, datetime):
            return candidate

        raw = str(candidate).strip()
        if not raw:
            return datetime.now().astimezone()

        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return datetime.now().astimezone()

        return parsed.astimezone() if parsed.tzinfo else parsed

    @staticmethod
    def _date_key(value: datetime) -> str:
        return value.strftime("%Y-%m-%d")

    @classmethod
    def _migrate_legacy_entries(cls) -> None:
        if DatabaseService.get_meta("journal_legacy_import_v1", "") == "done":
            return

        if cls._legacy_storage_path is None or not cls._legacy_storage_path.exists():
            DatabaseService.set_meta("journal_legacy_import_v1", "done")
            return

        try:
            raw = json.loads(cls._legacy_storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            DatabaseService.set_meta("journal_legacy_import_v1", "done")
            return

        if not isinstance(raw, list):
            DatabaseService.set_meta("journal_legacy_import_v1", "done")
            return

        for item in raw:
            if not isinstance(item, dict):
                continue
            member_account = str(item.get("member_account", "")).strip().lower()
            if not member_account:
                continue
            entry = cls._build_entry(member_account, item)
            cls._upsert_entry(entry)
            cls._sync_history_link(None, entry)

        DatabaseService.set_meta("journal_legacy_import_v1", "done")

    @classmethod
    def _export_entries_to_legacy_storage(cls) -> None:
        if cls._legacy_storage_path is None:
            return

        with DatabaseService.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    member_account,
                    food_name,
                    portion_label,
                    image_preview,
                    source,
                    created_at,
                    date_key,
                    calories,
                    protein,
                    fat,
                    carbs,
                    history_record_id
                FROM journal_entries
                ORDER BY created_at DESC
                """
            ).fetchall()

        entries = [cls._row_to_entry(row) for row in rows]
        cls._legacy_storage_path.parent.mkdir(parents=True, exist_ok=True)
        cls._legacy_storage_path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def _sync_history_link(cls, previous_history_record_id: int | None, entry: dict[str, Any]) -> None:
        next_history_record_id = cls._normalize_history_record_id(entry.get("history_record_id"))
        entry_id = str(entry.get("id", "")).strip()

        if previous_history_record_id and previous_history_record_id != next_history_record_id:
            HistoryService.detach_journal_entry(previous_history_record_id, entry_id)

        if next_history_record_id and entry_id:
            HistoryService.attach_journal_entry(next_history_record_id, entry_id)

    @classmethod
    def _sync_history_unlink(cls, entry: dict[str, Any]) -> None:
        history_record_id = cls._normalize_history_record_id(entry.get("history_record_id"))
        if history_record_id:
            HistoryService.detach_journal_entry(history_record_id, str(entry.get("id", "")).strip())
