from flask import Flask
from .config import Config
from .database import init_db
from .crypto_utils import ensure_keys

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    init_db(app)
    ensure_keys(app)
    from .routes import bp
    app.register_blueprint(bp)
    return app
