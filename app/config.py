from pathlib import Path
import os
import secrets

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DATABASE = BASE_DIR / "certificates.db"
    KEY_DIR = BASE_DIR / "keys"
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    INSTITUTION_NAME = os.environ.get("INSTITUTION_NAME", "Secure Academic Verification Authority")
