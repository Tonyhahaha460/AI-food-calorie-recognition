from __future__ import annotations

from functools import wraps
from http import HTTPStatus
from typing import Any, Callable

from flask import Blueprint, current_app, g, jsonify, request, send_from_directory

from app.data.food_profiles import get_dataset_dir
from app.services.auth_service import AuthError, AuthService
from app.services.history_service import HistoryService
from app.services.journal_service import JournalError, JournalService
from app.services.nutrition_service import FoodProfileError, NutritionService
from app.services.predictor import PredictionError, PredictorService
from app.services.training_service import TrainingError, TrainingService
from app.utils.image_utils import allowed_file, normalize_image_bytes

api_bp = Blueprint("api", __name__)


def _auth_header() -> str:
    return request.headers.get("Authorization", "")


def _current_user(optional: bool = True) -> dict[str, Any] | None:
    if not hasattr(g, "current_user"):
        g.current_user = AuthService.get_request_user(current_app.config, _auth_header())

    user = g.current_user
    if user is None and not optional:
        raise AuthError("請先登入。")
    return user


def _require_role(role: str) -> dict[str, Any]:
    user = _current_user(optional=False)
    if user is None or user.get("role") != role:
        raise AuthError("你沒有這個操作權限。")
    return user


def _auth_error_response(exc: AuthError) -> tuple[Any, int]:
    message = str(exc)
    status = HTTPStatus.UNAUTHORIZED if "登入" in message else HTTPStatus.FORBIDDEN
    return jsonify({"error": message}), status


def require_auth(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            _current_user(optional=False)
        except AuthError as exc:
            return _auth_error_response(exc)
        return view(*args, **kwargs)

    return wrapped


def require_admin(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            _require_role("admin")
        except AuthError as exc:
            return _auth_error_response(exc)
        return view(*args, **kwargs)

    return wrapped


def require_member(view: Callable) -> Callable:
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            _require_role("member")
        except AuthError as exc:
            return _auth_error_response(exc)
        return view(*args, **kwargs)

    return wrapped


def _get_history_context() -> dict[str, str]:
    user = _current_user(optional=True)
    if not user:
        return {
            "member_account": "",
            "member_name": "",
            "viewer_role": "visitor",
        }

    return {
        "member_account": str(user.get("account", "")).strip() if user.get("role") == "member" else "",
        "member_name": str(user.get("name", "")).strip(),
        "viewer_role": str(user.get("role", "visitor")).strip() or "visitor",
    }


@api_bp.post("/api/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    try:
        result = AuthService.login(
            current_app.config,
            payload.get("account", ""),
            payload.get("password", ""),
        )
    except AuthError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.UNAUTHORIZED

    return jsonify(result), HTTPStatus.OK


@api_bp.post("/api/auth/register")
def register():
    payload = request.get_json(silent=True) or {}
    try:
        result = AuthService.register_member(current_app.config, payload)
    except AuthError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify(result), HTTPStatus.CREATED


@api_bp.get("/api/auth/me")
@require_auth
def current_user():
    return jsonify({"user": _current_user(optional=False)}), HTTPStatus.OK


@api_bp.put("/api/auth/me")
@require_auth
def update_current_user():
    try:
        user = AuthService.update_profile(_current_user(optional=False), request.get_json(silent=True) or {})
    except AuthError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify({"user": user}), HTTPStatus.OK


@api_bp.get("/api/journal")
@require_member
def list_journal_entries():
    user = _current_user(optional=False)
    items = JournalService.list_entries(
        member_account=str(user.get("account", "")).strip(),
        date_key=request.args.get("date_key", ""),
    )
    return jsonify({"items": items}), HTTPStatus.OK


@api_bp.post("/api/journal")
@require_member
def create_journal_entry():
    user = _current_user(optional=False)
    try:
        item = JournalService.create_entry(
            member_account=str(user.get("account", "")).strip(),
            payload=request.get_json(silent=True) or {},
        )
    except JournalError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify({"item": item}), HTTPStatus.CREATED


@api_bp.put("/api/journal/<entry_id>")
@require_member
def update_journal_entry(entry_id: str):
    user = _current_user(optional=False)
    try:
        item = JournalService.update_entry(
            member_account=str(user.get("account", "")).strip(),
            entry_id=entry_id,
            patch=request.get_json(silent=True) or {},
        )
    except JournalError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify({"item": item}), HTTPStatus.OK


@api_bp.delete("/api/journal/<entry_id>")
@require_member
def delete_journal_entry(entry_id: str):
    user = _current_user(optional=False)
    try:
        JournalService.delete_entry(
            member_account=str(user.get("account", "")).strip(),
            entry_id=entry_id,
        )
    except JournalError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify({"message": "Journal entry deleted."}), HTTPStatus.OK


@api_bp.get("/api/health")
@api_bp.get("/health")
def health_check():
    return jsonify(
        {
            "status": "ok",
            "service": "ai-meal-scanner-api",
            "model_provider": current_app.config["MODEL_PROVIDER"],
            "trained_model": TrainingService.status(current_app.config)["available"],
        }
    )


@api_bp.post("/predict")
def predict():
    image = request.files.get("image")

    if image is None or image.filename == "":
        return (
            jsonify({"error": "Please upload a JPG or PNG image using the 'image' field."}),
            HTTPStatus.BAD_REQUEST,
        )

    predictor = PredictorService(current_app.config)

    try:
        result = predictor.predict(image, history_context=_get_history_context())
    except PredictionError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception:
        return jsonify({"error": "Prediction failed due to an unexpected server error."}), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify(result), HTTPStatus.OK


@api_bp.get("/history")
@api_bp.get("/api/history")
def history():
    user = _current_user(optional=True)
    include_all = request.args.get("include_all", "").strip().lower() in {"1", "true", "yes"}
    requested_member_account = str(request.args.get("member_account", "")).strip().lower()

    if not user:
        items: list[dict[str, Any]] = []
    elif user.get("role") == "admin":
        if include_all or not requested_member_account:
            items = HistoryService.list_records(include_all=True)
        else:
            items = HistoryService.list_records(member_account=requested_member_account, include_all=False)
    else:
        items = HistoryService.list_records(member_account=user.get("account", ""), include_all=False)

    return jsonify({"items": items}), HTTPStatus.OK


@api_bp.get("/api/food-profiles")
def list_food_profiles():
    return jsonify({"items": NutritionService.format_profiles_for_response()}), HTTPStatus.OK


@api_bp.post("/api/food-profiles")
@require_admin
def create_food_profile():
    try:
        profile = NutritionService.create_profile(request.get_json(silent=True) or {})
    except FoodProfileError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify(profile), HTTPStatus.CREATED


@api_bp.put("/api/food-profiles/<label>")
@require_admin
def update_food_profile(label: str):
    try:
        profile = NutritionService.update_profile(label, request.get_json(silent=True) or {})
    except FoodProfileError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify(profile), HTTPStatus.OK


@api_bp.delete("/api/food-profiles/<label>")
@require_admin
def delete_food_profile(label: str):
    try:
        NutritionService.delete_profile(label)
    except FoodProfileError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify({"message": "Food profile deleted."}), HTTPStatus.OK


@api_bp.post("/api/food-profiles/<label>/images")
@require_admin
def upload_food_profile_images(label: str):
    files = request.files.getlist("images")
    try:
        result = NutritionService.add_training_images(label, files)
    except FoodProfileError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify(result), HTTPStatus.CREATED


@api_bp.post("/api/training-feedback")
@require_member
def upload_training_feedback():
    image = request.files.get("image")
    raw_label = (
        request.form.get("label", "")
        or request.form.get("food_label", "")
        or request.form.get("food_name", "")
    )
    food_name = request.form.get("food_name", "")
    label = NutritionService.resolve_lookup_label(raw_label) or NutritionService.resolve_lookup_label(food_name)
    if not label:
        label = raw_label

    if image is None or image.filename == "":
        return jsonify({"error": "Please upload a JPG or PNG image using the 'image' field."}), HTTPStatus.BAD_REQUEST
    if not allowed_file(image.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        return jsonify({"error": "Only JPG and PNG images are supported."}), HTTPStatus.BAD_REQUEST

    image_bytes = image.read()
    try:
        normalized_bytes = normalize_image_bytes(image_bytes)
        result = NutritionService.add_training_image_bytes(label, image.filename, normalized_bytes)
    except FoodProfileError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception:
        return jsonify({"error": "Training feedback image could not be saved."}), HTTPStatus.BAD_REQUEST

    return jsonify(result), HTTPStatus.CREATED


@api_bp.get("/api/food-profiles/<label>/images")
@require_admin
def list_food_profile_images(label: str):
    try:
        result = NutritionService.get_training_images(label)
    except FoodProfileError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify(result), HTTPStatus.OK


@api_bp.get("/api/food-profiles/<label>/images/<path:filename>")
def get_food_profile_image(label: str, filename: str):
    directory = get_dataset_dir(label)
    return send_from_directory(directory, filename)


@api_bp.delete("/api/food-profiles/<label>/images/<path:filename>")
@require_admin
def delete_food_profile_image(label: str, filename: str):
    try:
        result = NutritionService.delete_training_image(label, filename)
    except FoodProfileError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST

    return jsonify(result), HTTPStatus.OK


@api_bp.get("/api/train/status")
@require_admin
def training_status():
    return jsonify(TrainingService.status(current_app.config)), HTTPStatus.OK


@api_bp.post("/api/train")
@require_admin
def train_model():
    try:
        result = TrainingService.train(current_app.config)
    except TrainingError as exc:
        return jsonify({"error": str(exc)}), HTTPStatus.BAD_REQUEST
    except Exception:
        return jsonify({"error": "Training failed due to an unexpected server error."}), HTTPStatus.INTERNAL_SERVER_ERROR

    return jsonify(result), HTTPStatus.OK
