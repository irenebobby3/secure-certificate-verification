import base64
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

def ensure_keys(app):
    key_dir = Path(app.config["KEY_DIR"])
    key_dir.mkdir(parents=True, exist_ok=True)
    private_path = key_dir / "private_key.pem"
    public_path = key_dir / "public_key.pem"
    if not private_path.exists():
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_path.write_bytes(private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ))
        public_path.write_bytes(private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

def canonical_data(cert):
    values = [cert["certificate_id"], cert["student_name"], cert["course"],
              cert["institution"], cert["issue_date"], cert.get("description", "")]
    return "|".join(str(v).strip() for v in values).encode("utf-8")

def calculate_hash(cert):
    return hashlib.sha256(canonical_data(cert)).hexdigest()

def load_private_key(app):
    return serialization.load_pem_private_key(
        (Path(app.config["KEY_DIR"]) / "private_key.pem").read_bytes(), password=None)

def load_public_key(app):
    return serialization.load_pem_public_key(
        (Path(app.config["KEY_DIR"]) / "public_key.pem").read_bytes())

def sign_hash(app, digest_hex):
    private_key = load_private_key(app)
    signature = private_key.sign(
        bytes.fromhex(digest_hex),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")

def verify_signature(app, digest_hex, signature_b64):
    try:
        load_public_key(app).verify(
            base64.b64decode(signature_b64),
            bytes.fromhex(digest_hex),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
