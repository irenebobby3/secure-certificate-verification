# Secure Certificate Verification System

Full-stack Applied Cryptography project using Flask, SQLite, SHA-256, RSA-PSS digital signatures, QR codes, and PDF certificates.

## Run

```bash
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Configure the admin login and session secret before starting the app. In Windows PowerShell:

```powershell
$env:ADMIN_USERNAME = "admin"
$env:ADMIN_PASSWORD = "choose-a-strong-password"
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
python run.py
```

On macOS/Linux, set the same variables with `export` before running `python run.py`. Open http://127.0.0.1:5000. If admin credentials are not configured, admin login is disabled. A random session secret is generated at startup when `SECRET_KEY` is unset; set a persistent secret in the deployment environment so sessions remain valid across restarts. Debug mode is off by default; enable it only for local development with `FLASK_DEBUG=1`.

## Main flow
1. Admin logs in.
2. Admin issues a certificate.
3. Backend canonicalizes certificate fields and calculates SHA-256.
4. RSA private key signs the digest using RSA-PSS.
5. Certificate data, hash, and signature are stored in SQLite.
6. PDF certificate contains a QR code pointing to the verification page.
7. Anyone can verify by Certificate ID or QR code.
8. Backend recalculates the hash and verifies the RSA signature.
9. Any changed certificate field causes verification to fail.

## Security note
Educational project only; it is not production-ready. Before real deployment, add password hashing, CSRF protection, login rate limiting, HTTPS, secure and persistent secret/key management, audit logging, and a production database and WSGI server. Do not use real student data in a public demo. The database and generated PEM keys are ignored by Git; verify they are not already tracked before publishing.
