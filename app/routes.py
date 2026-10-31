from datetime import date, datetime
from functools import wraps
import io
import qrcode
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from .database import get_db
from .crypto_utils import calculate_hash, sign_hash, verify_signature

bp = Blueprint("main", __name__)

def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("main.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def make_certificate_id():
    prefix = datetime.now().strftime("CERT-%Y%m%d")
    count = get_db().execute("SELECT COUNT(*) AS c FROM certificates WHERE certificate_id LIKE ?", (prefix + "-%",)).fetchone()["c"]
    return f"{prefix}-{count + 1:04d}"

def verify_cert(cert):
    recalculated = calculate_hash(cert)
    hash_match = recalculated == cert["certificate_hash"]
    signature_valid = verify_signature(current_app, cert["certificate_hash"], cert["signature"])
    return recalculated, hash_match, signature_valid, hash_match and signature_valid

def build_pdf(cert):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setTitle(cert["certificate_id"])
    c.setLineWidth(2); c.rect(18*mm, 18*mm, w-36*mm, h-36*mm)
    c.setLineWidth(.6); c.rect(23*mm, 23*mm, w-46*mm, h-46*mm)
    c.setFont("Helvetica-Bold", 24); c.drawCentredString(w/2, h-60*mm, cert["institution"])
    c.setFont("Helvetica", 12); c.drawCentredString(w/2, h-72*mm, "DIGITAL CERTIFICATE OF ACHIEVEMENT")
    c.setFont("Helvetica-Bold", 18); c.drawCentredString(w/2, h-92*mm, cert["student_name"])
    c.setFont("Helvetica", 12); c.drawCentredString(w/2, h-106*mm, f"has successfully completed: {cert['course']}")
    if cert["description"]:
        c.setFont("Helvetica", 10); c.drawCentredString(w/2, h-120*mm, cert["description"][:100])
    c.setFont("Helvetica", 10); c.drawString(35*mm, 42*mm, f"Certificate ID: {cert['certificate_id']}")
    c.drawString(35*mm, 35*mm, f"Issue Date: {cert['issue_date']}")
    verify_url = url_for("main.verify", id=cert["certificate_id"], _external=True)
    qr = qrcode.make(verify_url); qbuf = io.BytesIO(); qr.save(qbuf, format="PNG"); qbuf.seek(0)
    c.drawImage(ImageReader(qbuf), w-62*mm, 30*mm, 30*mm, 30*mm)
    c.setFont("Helvetica", 7); c.drawString(35*mm, 27*mm, "Scan QR code to verify this certificate.")
    c.save(); buf.seek(0); return buf

@bp.route("/")
def index(): return render_template("index.html") 

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (current_app.config["ADMIN_USERNAME"] and current_app.config["ADMIN_PASSWORD"]
                and request.form.get("username") == current_app.config["ADMIN_USERNAME"]
                and request.form.get("password") == current_app.config["ADMIN_PASSWORD"]):
            session["admin_logged_in"] = True
            return redirect(request.args.get("next") or url_for("main.dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")

@bp.route("/logout")
def logout(): session.clear(); return redirect(url_for("main.index"))

@bp.route("/dashboard")
@admin_required
def dashboard():
    rows = get_db().execute("SELECT * FROM certificates ORDER BY id DESC").fetchall()
    return render_template("dashboard.html", certificates=rows)

@bp.route("/issue", methods=["GET", "POST"])
@admin_required
def issue():
    if request.method == "POST":
        fields = {k: request.form.get(k, "").strip() for k in ["student_name", "course", "institution", "issue_date", "description"]}
        if not all(fields[k] for k in ["student_name", "course", "institution", "issue_date"]):
            flash("Please fill in all required fields.", "danger"); return render_template("issue.html", today=date.today().isoformat())
        fields["certificate_id"] = make_certificate_id()
        digest = calculate_hash(fields); signature = sign_hash(current_app, digest)
        db = get_db(); db.execute("""INSERT INTO certificates
        (certificate_id, student_name, course, institution, issue_date, description, certificate_hash, signature, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", (fields["certificate_id"], fields["student_name"], fields["course"], fields["institution"], fields["issue_date"], fields["description"], digest, signature, datetime.now().isoformat(timespec="seconds")))
        db.commit(); flash(f"Certificate {fields['certificate_id']} created successfully.", "success")
        return redirect(url_for("main.certificate", certificate_id=fields["certificate_id"]))
    return render_template("issue.html", today=date.today().isoformat())

@bp.route("/certificate/<certificate_id>")
@admin_required
def certificate(certificate_id):
    cert = get_db().execute("SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)).fetchone()
    if not cert: flash("Certificate not found.", "danger"); return redirect(url_for("main.dashboard"))
    return render_template("certificate.html", cert=cert)

@bp.route("/certificate/<certificate_id>/pdf")
def certificate_pdf(certificate_id):
    cert = get_db().execute("SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)).fetchone()
    if not cert: return "Certificate not found", 404
    return send_file(build_pdf(dict(cert)), mimetype="application/pdf", as_attachment=True, download_name=f"{certificate_id}.pdf")

@bp.route("/verify", methods=["GET", "POST"])
def verify():
    certificate_id = (request.args.get("id") if request.method == "GET" else request.form.get("certificate_id", "")) or ""
    certificate_id = certificate_id.strip(); cert = None; valid = None; recalculated = None; hash_match = None; signature_valid = None
    if certificate_id:
        row = get_db().execute("SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)).fetchone()
        if row:
            cert = dict(row); recalculated, hash_match, signature_valid, valid = verify_cert(cert)
    return render_template("verify.html", cert=cert, valid=valid, recalculated_hash=recalculated, hash_match=hash_match, signature_valid=signature_valid, certificate_id=certificate_id)

@bp.route("/api/verify/<certificate_id>")
def api_verify(certificate_id):
    row = get_db().execute("SELECT * FROM certificates WHERE certificate_id = ?", (certificate_id,)).fetchone()
    if not row: return jsonify({"certificate_id": certificate_id, "valid": False, "message": "Certificate not found"}), 404
    cert = dict(row); recalculated, hash_match, signature_valid, valid = verify_cert(cert)
    return jsonify({"certificate_id": cert["certificate_id"], "valid": valid, "student_name": cert["student_name"], "course": cert["course"], "institution": cert["institution"], "issue_date": cert["issue_date"], "stored_sha256": cert["certificate_hash"], "recalculated_sha256": recalculated, "hash_matches": hash_match, "signature_valid": signature_valid})
