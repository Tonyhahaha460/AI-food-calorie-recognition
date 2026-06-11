from flask import Flask
from flask_cors import CORS

from .api.routes import api_bp
from .core.config import Config
from .services.auth_service import AuthService
from .services.database_service import DatabaseService
from .services.history_service import HistoryService
from .services.journal_service import JournalService


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config())
    DatabaseService.configure(app.config)
    AuthService.configure(app.config)
    HistoryService.configure(app.config)
    JournalService.configure(app.config)

    CORS(
        app,
        resources={
            r"/predict": {"origins": app.config["CORS_ORIGINS"]},
            r"/api/*": {"origins": app.config["CORS_ORIGINS"]},
        },
    )

    app.register_blueprint(api_bp)

    return app
