import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(self) -> None:
        self.DEBUG = os.getenv("FLASK_ENV", "development") == "development"
        self.PORT = int(os.getenv("PORT", "5000"))
        self.MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(4 * 1024 * 1024)))
        self.ALLOWED_EXTENSIONS = {
            extension.strip().lower()
            for extension in os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png").split(",")
            if extension.strip()
        }
        self.CORS_ORIGINS = [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
        self.DATABASE_PATH = os.getenv(
            "DATABASE_PATH",
            "local_assets/backend/database/app.db",
        )
        self.HISTORY_STORAGE_PATH = os.getenv(
            "HISTORY_STORAGE_PATH",
            "local_assets/backend/history/analysis_history.json",
        )
        self.HISTORY_MAX_RECORDS = int(os.getenv("HISTORY_MAX_RECORDS", "50"))
        self.JOURNAL_STORAGE_PATH = os.getenv(
            "JOURNAL_STORAGE_PATH",
            "local_assets/backend/journal/journal_entries.json",
        )
        self.AUTH_STORAGE_PATH = os.getenv(
            "AUTH_STORAGE_PATH",
            "local_assets/backend/auth/members.json",
        )
        self.AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "ai-meal-scanner-dev-secret")
        self.AUTH_TOKEN_MAX_AGE = int(os.getenv("AUTH_TOKEN_MAX_AGE", str(60 * 60 * 24 * 7)))
        self.MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "mock")
        self.TRAINED_MODEL_PATH = os.getenv(
            "TRAINED_MODEL_PATH",
            "../local_assets/backend/model_artifacts/meal_classifier.pkl",
        )
        self.ALL_FOOD_CLASSIFIER_MODEL_PATH = os.getenv(
            "ALL_FOOD_CLASSIFIER_MODEL_PATH",
            "runs/all_food_cls/uec_food101_yolov8n_cls-3/weights/best.pt",
        )
        self.SECONDARY_FOOD_CLASSIFIER_MODEL_PATH = os.getenv(
            "SECONDARY_FOOD_CLASSIFIER_MODEL_PATH",
            "runs/downloaded_food_cls/downloaded_web_images_yolov8n_cls_20260509_130957/weights/best.pt",
        )
        self.MOBILENET_REGRESSION_MODEL_PATH = os.getenv(
            "MOBILENET_REGRESSION_MODEL_PATH",
            "../local_assets/backend/model_artifacts/mobilenet_regressor.pt",
        )
        self.MOBILENET_REGRESSION_SUMMARY_PATH = os.getenv(
            "MOBILENET_REGRESSION_SUMMARY_PATH",
            "../local_assets/backend/model_artifacts/training_summary.json",
        )
        self.NUTRITION5K_ROOT = os.getenv("NUTRITION5K_ROOT", "../local_assets/backend/dataset/nutrition5k")
        self.NUTRITION5K_METADATA_PATH = os.getenv(
            "NUTRITION5K_METADATA_PATH",
            "app/data/nutrition5k_metadata.json",
        )
        self.FOOD101_ROOT = os.getenv("FOOD101_ROOT", "../local_assets/backend/dataset")
        self.FOOD101_USE = os.getenv("FOOD101_USE", "false").lower() == "true"
        self.FOOD101_DOWNLOAD_ON_TRAIN = os.getenv("FOOD101_DOWNLOAD_ON_TRAIN", "false").lower() == "true"
        self.FOOD101_TRAIN_SAMPLES_PER_LABEL = int(os.getenv("FOOD101_TRAIN_SAMPLES_PER_LABEL", "120"))
        self.FOOD101_VAL_SAMPLES_PER_LABEL = int(os.getenv("FOOD101_VAL_SAMPLES_PER_LABEL", "40"))
        self.CUSTOM_TRAIN_REPEAT = int(os.getenv("CUSTOM_TRAIN_REPEAT", "12"))
        self.CHINESE_FOOD_MODEL_NAME = os.getenv(
            "CHINESE_FOOD_MODEL_NAME",
            "Albertbeta123/resnet-50-chinese-food",
        )
        self.CHINESE_TOP_K = int(os.getenv("CHINESE_TOP_K", "3"))
        self.CHINESE_CONFIDENCE_THRESHOLD = float(os.getenv("CHINESE_CONFIDENCE_THRESHOLD", "0.80"))
        self.GENERAL_CONFIDENCE_THRESHOLD = float(os.getenv("GENERAL_CONFIDENCE_THRESHOLD", "0.65"))
        self.MIN_ACCEPTED_CONFIDENCE = float(os.getenv("MIN_ACCEPTED_CONFIDENCE", "0.72"))
        self.YOLO_CLS_MIN_ACCEPTED_CONFIDENCE = float(
            os.getenv("YOLO_CLS_MIN_ACCEPTED_CONFIDENCE", "0.45")
        )
        self.YOLO_CLS_MIN_CONFIDENCE_MARGIN = float(
            os.getenv("YOLO_CLS_MIN_CONFIDENCE_MARGIN", "0.12")
        )
        self.SECONDARY_YOLO_CLS_MIN_ACCEPTED_CONFIDENCE = float(
            os.getenv("SECONDARY_YOLO_CLS_MIN_ACCEPTED_CONFIDENCE", "0.45")
        )
        self.SECONDARY_YOLO_CLS_MIN_CONFIDENCE_MARGIN = float(
            os.getenv("SECONDARY_YOLO_CLS_MIN_CONFIDENCE_MARGIN", "0.12")
        )
        self.LOCAL_PRIORITY_THRESHOLD = float(os.getenv("LOCAL_PRIORITY_THRESHOLD", "0.78"))
        self.HYBRID_SCORE_MARGIN = float(os.getenv("HYBRID_SCORE_MARGIN", "0.08"))
        self.YOLO_MODEL_NAME = os.getenv("YOLO_MODEL_NAME", "yolov8n.pt")
        self.HF_IMAGE_CLASSIFIER_MODEL = os.getenv("HF_IMAGE_CLASSIFIER_MODEL", "nateraw/food")
        self.YOLO_DETECTION_CONFIDENCE = float(os.getenv("YOLO_DETECTION_CONFIDENCE", "0.25"))
        self.YOLO_MAX_DETECTIONS = int(os.getenv("YOLO_MAX_DETECTIONS", "6"))
        self.HF_CLASSIFIER_TOP_K = int(os.getenv("HF_CLASSIFIER_TOP_K", "5"))
        self.YOLO_HF_DIRECT_ACCEPT_THRESHOLD = float(
            os.getenv("YOLO_HF_DIRECT_ACCEPT_THRESHOLD", "0.90")
        )
        self.AUTO_DETECTION_MIN_CONFIDENCE = float(os.getenv("AUTO_DETECTION_MIN_CONFIDENCE", "0.62"))
        self.AUTO_SINGLE_ITEM_ACCEPT_CONFIDENCE = float(
            os.getenv("AUTO_SINGLE_ITEM_ACCEPT_CONFIDENCE", "0.85")
        )
        self.AUTO_MULTI_ITEM_COUNT = int(os.getenv("AUTO_MULTI_ITEM_COUNT", "2"))
