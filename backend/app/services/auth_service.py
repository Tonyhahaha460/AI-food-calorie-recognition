from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from itsdangerous import BadSignature, BadTimeSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from .database_service import DatabaseService


class AuthError(Exception):
    pass


class AuthService:
    DEMO_MEMBER = {
        "account": "member",
        "name": "示範會員",
        "password": "1234",
        "gender": "male",
        "heightCm": 170,
        "weightKg": 65,
        "age": 22,
        "activityLevel": "moderate",
        "role": "member",
    }

    DEMO_ADMIN = {
        "account": "admin",
        "name": "示範管理員",
        "password": "1234",
        "role": "admin",
    }

    VALID_GENDERS = {"male", "female"}
    VALID_ACTIVITY_LEVELS = {"sedentary", "light", "moderate", "active", "very_active"}

    _legacy_storage_path: Path | None = None
    _configured = False

    @classmethod
    def configure(cls, config: dict[str, Any]) -> None:
        DatabaseService.configure(config)

        project_root = Path(__file__).resolve().parents[3]
        configured_path = str(config.get("AUTH_STORAGE_PATH", "")).strip()
        path = Path(configured_path) if configured_path else Path("local_assets/backend/auth/members.json")
        if not path.is_absolute():
            path = (project_root / path).resolve()

        if cls._configured and cls._legacy_storage_path == path:
            return

        cls._legacy_storage_path = path
        cls._seed_demo_member()
        cls._migrate_legacy_members()
        cls._configured = True

    @classmethod
    def login(cls, config: dict[str, Any], account: str, password: str) -> dict[str, Any]:
        normalized_account = cls._normalize_account(account)
        normalized_password = str(password or "")

        if not normalized_account or not normalized_password:
            raise AuthError("請輸入帳號和密碼。")

        if normalized_account == cls.DEMO_ADMIN["account"] and normalized_password == cls.DEMO_ADMIN["password"]:
            user = cls._public_admin()
            return {"token": cls._issue_token(config, user), "user": user}

        member = cls._fetch_member_record(normalized_account)
        if member is None or not check_password_hash(member["password_hash"], normalized_password):
            raise AuthError("帳號或密碼錯誤。")

        user = cls._public_member(member)
        return {"token": cls._issue_token(config, user), "user": user}

    @classmethod
    def register_member(cls, config: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        member = cls._build_member_record(payload)
        account = member["account"]

        if account == cls.DEMO_ADMIN["account"] or cls._fetch_member_record(account) is not None:
            raise AuthError("這個帳號已經有人使用。")

        cls._upsert_member_record(member)
        user = cls._public_member(member)
        return {"token": cls._issue_token(config, user), "user": user}

    @classmethod
    def update_profile(cls, actor: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        if actor.get("role") != "member":
            raise AuthError("只有會員可以修改自己的資料。")

        account = cls._normalize_account(actor.get("account", ""))
        member = cls._fetch_member_record(account)
        if member is None:
            raise AuthError("找不到這個會員。")

        next_record = deepcopy(member)
        if "name" in payload:
            next_record["name"] = cls._normalize_name(payload.get("name"), account)
        if "gender" in payload:
            next_record["gender"] = cls._normalize_gender(payload.get("gender"))
        if "activityLevel" in payload:
            next_record["activityLevel"] = cls._normalize_activity_level(payload.get("activityLevel"))
        if "heightCm" in payload:
            next_record["heightCm"] = cls._normalize_positive_number(payload.get("heightCm"), "請輸入正確的身高。")
        if "weightKg" in payload:
            next_record["weightKg"] = cls._normalize_positive_number(payload.get("weightKg"), "請輸入正確的體重。")
        if "age" in payload:
            next_record["age"] = int(cls._normalize_positive_number(payload.get("age"), "請輸入正確的年齡。", allow_float=False))

        next_record["updatedAt"] = datetime.now(timezone.utc).isoformat()
        cls._upsert_member_record(next_record)
        return cls._public_member(next_record)

    @classmethod
    def get_request_user(cls, config: dict[str, Any], auth_header: str) -> dict[str, Any] | None:
        token = cls._extract_bearer_token(auth_header)
        if not token:
            return None
        return cls.verify_token(config, token)

    @classmethod
    def verify_token(cls, config: dict[str, Any], token: str) -> dict[str, Any]:
        serializer = cls._serializer(config)
        max_age = int(config.get("AUTH_TOKEN_MAX_AGE", 60 * 60 * 24 * 7))

        try:
            payload = serializer.loads(token, max_age=max_age)
        except SignatureExpired as exc:
            raise AuthError("登入已過期，請重新登入。") from exc
        except (BadSignature, BadTimeSignature) as exc:
            raise AuthError("登入資訊無效，請重新登入。") from exc

        role = str(payload.get("role", "")).strip()
        account = cls._normalize_account(payload.get("account", ""))

        if role == "admin" and account == cls.DEMO_ADMIN["account"]:
            return cls._public_admin()

        if role != "member":
            raise AuthError("登入資訊無效，請重新登入。")

        member = cls._fetch_member_record(account)
        if member is None:
            raise AuthError("找不到這個會員，請重新登入。")

        return cls._public_member(member)

    @classmethod
    def _seed_demo_member(cls) -> None:
        existing = cls._fetch_member_record(cls.DEMO_MEMBER["account"])
        now = datetime.now(timezone.utc).isoformat()

        if existing is None:
            member = cls._build_member_record(cls.DEMO_MEMBER)
            member["createdAt"] = now
            member["updatedAt"] = now
            cls._upsert_member_record(member)
            return

        existing.update(
            {
                "name": cls.DEMO_MEMBER["name"],
                "gender": cls.DEMO_MEMBER["gender"],
                "heightCm": cls.DEMO_MEMBER["heightCm"],
                "weightKg": cls.DEMO_MEMBER["weightKg"],
                "age": cls.DEMO_MEMBER["age"],
                "activityLevel": cls.DEMO_MEMBER["activityLevel"],
                "role": "member",
                "updatedAt": now,
            }
        )
        if not str(existing.get("password_hash", "")).strip():
            existing["password_hash"] = generate_password_hash(cls.DEMO_MEMBER["password"])
        cls._upsert_member_record(existing)

    @classmethod
    def _migrate_legacy_members(cls) -> None:
        if DatabaseService.get_meta("auth_legacy_import_v1", "") == "done":
            return

        if cls._legacy_storage_path is None or not cls._legacy_storage_path.exists():
            DatabaseService.set_meta("auth_legacy_import_v1", "done")
            return

        try:
            raw = json.loads(cls._legacy_storage_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            DatabaseService.set_meta("auth_legacy_import_v1", "done")
            return

        if not isinstance(raw, list):
            DatabaseService.set_meta("auth_legacy_import_v1", "done")
            return

        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                account = cls._normalize_account(item.get("account", ""))
                password_hash = str(item.get("password_hash", "")).strip()
                if not account or not password_hash or account == cls.DEMO_ADMIN["account"]:
                    continue
                if cls._fetch_member_record(account) is not None:
                    continue

                member = {
                    "account": account,
                    "password_hash": password_hash,
                    "name": cls._normalize_name(item.get("name"), account),
                    "gender": cls._normalize_gender(item.get("gender")),
                    "heightCm": cls._normalize_positive_number(item.get("heightCm", 0), "請輸入正確的身高。"),
                    "weightKg": cls._normalize_positive_number(item.get("weightKg", 0), "請輸入正確的體重。"),
                    "age": int(cls._normalize_positive_number(item.get("age", 0), "請輸入正確的年齡。", allow_float=False)),
                    "activityLevel": cls._normalize_activity_level(item.get("activityLevel")),
                    "role": "member",
                    "createdAt": datetime.now(timezone.utc).isoformat(),
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                }
                cls._upsert_member_record(member)
            except AuthError:
                continue

        DatabaseService.set_meta("auth_legacy_import_v1", "done")

    @classmethod
    def _fetch_member_record(cls, account: str) -> dict[str, Any] | None:
        with DatabaseService.connect() as conn:
            row = conn.execute(
                """
                SELECT account, password_hash, name, gender, height_cm, weight_kg, age, activity_level, role, created_at, updated_at
                FROM members
                WHERE account = ?
                """,
                (account,),
            ).fetchone()

        if row is None:
            return None

        return {
            "account": row["account"],
            "password_hash": row["password_hash"],
            "name": row["name"],
            "gender": row["gender"],
            "heightCm": float(row["height_cm"]),
            "weightKg": float(row["weight_kg"]),
            "age": int(row["age"]),
            "activityLevel": row["activity_level"],
            "role": row["role"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    @classmethod
    def _upsert_member_record(cls, member: dict[str, Any]) -> None:
        created_at = str(member.get("createdAt") or datetime.now(timezone.utc).isoformat())
        updated_at = str(member.get("updatedAt") or datetime.now(timezone.utc).isoformat())

        with DatabaseService.connect() as conn:
            conn.execute(
                """
                INSERT INTO members(
                    account,
                    password_hash,
                    name,
                    gender,
                    height_cm,
                    weight_kg,
                    age,
                    activity_level,
                    role,
                    created_at,
                    updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(account) DO UPDATE SET
                    password_hash = excluded.password_hash,
                    name = excluded.name,
                    gender = excluded.gender,
                    height_cm = excluded.height_cm,
                    weight_kg = excluded.weight_kg,
                    age = excluded.age,
                    activity_level = excluded.activity_level,
                    role = excluded.role,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                (
                    member["account"],
                    member["password_hash"],
                    member["name"],
                    member["gender"],
                    float(member["heightCm"]),
                    float(member["weightKg"]),
                    int(member["age"]),
                    member["activityLevel"],
                    member.get("role", "member"),
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()

    @classmethod
    def _build_member_record(
        cls,
        payload: dict[str, Any],
        allow_existing_password: bool = False,
    ) -> dict[str, Any]:
        account = cls._normalize_account(payload.get("account", ""))
        password = str(payload.get("password", "") or "")
        password_hash = str(payload.get("password_hash", "") or "")

        if not account:
            raise AuthError("請輸入會員帳號。")

        if not password and not (allow_existing_password and password_hash):
            raise AuthError("請輸入密碼。")

        now = datetime.now(timezone.utc).isoformat()
        return {
            "account": account,
            "password_hash": password_hash or generate_password_hash(password),
            "name": cls._normalize_name(payload.get("name"), account),
            "gender": cls._normalize_gender(payload.get("gender")),
            "heightCm": cls._normalize_positive_number(payload.get("heightCm"), "請輸入正確的身高。"),
            "weightKg": cls._normalize_positive_number(payload.get("weightKg"), "請輸入正確的體重。"),
            "age": int(cls._normalize_positive_number(payload.get("age"), "請輸入正確的年齡。", allow_float=False)),
            "activityLevel": cls._normalize_activity_level(payload.get("activityLevel")),
            "role": "member",
            "createdAt": now,
            "updatedAt": now,
        }

    @classmethod
    def _public_member(cls, member: dict[str, Any]) -> dict[str, Any]:
        return {
            "account": member["account"],
            "name": member["name"],
            "role": "member",
            "gender": member["gender"],
            "heightCm": member["heightCm"],
            "weightKg": member["weightKg"],
            "age": member["age"],
            "activityLevel": member["activityLevel"],
        }

    @classmethod
    def _public_admin(cls) -> dict[str, Any]:
        return {
            "account": cls.DEMO_ADMIN["account"],
            "name": cls.DEMO_ADMIN["name"],
            "role": "admin",
            "gender": "male",
            "heightCm": 0,
            "weightKg": 0,
            "age": 0,
            "activityLevel": "sedentary",
        }

    @staticmethod
    def _normalize_account(value: Any) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _normalize_name(value: Any, fallback_account: str) -> str:
        return str(value or "").strip() or fallback_account

    @classmethod
    def _normalize_gender(cls, value: Any) -> str:
        gender = str(value or "").strip().lower()
        if gender not in cls.VALID_GENDERS:
            raise AuthError("請選擇正確的性別。")
        return gender

    @classmethod
    def _normalize_activity_level(cls, value: Any) -> str:
        activity_level = str(value or "").strip().lower()
        if activity_level not in cls.VALID_ACTIVITY_LEVELS:
            raise AuthError("請選擇正確的活動量。")
        return activity_level

    @staticmethod
    def _normalize_positive_number(value: Any, error_message: str, allow_float: bool = True) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise AuthError(error_message) from exc

        if number <= 0:
            raise AuthError(error_message)

        return number if allow_float else float(int(number))

    @staticmethod
    def _extract_bearer_token(auth_header: str) -> str:
        raw = str(auth_header or "").strip()
        if not raw.lower().startswith("bearer "):
            return ""
        return raw[7:].strip()

    @staticmethod
    def _serializer(config: dict[str, Any]) -> URLSafeTimedSerializer:
        return URLSafeTimedSerializer(
            str(config.get("AUTH_SECRET_KEY", "ai-meal-scanner-dev-secret")),
            salt="ai-meal-scanner-auth",
        )

    @classmethod
    def _issue_token(cls, config: dict[str, Any], user: dict[str, Any]) -> str:
        serializer = cls._serializer(config)
        return serializer.dumps({"account": user["account"], "role": user["role"]})
