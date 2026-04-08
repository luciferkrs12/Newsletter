from flask import Flask, render_template, request, redirect, session, send_file, flash
import os
import smtplib
import secrets
from io import BytesIO
from pathlib import Path
from email.message import EmailMessage
from datetime import datetime, timedelta
import pdfkit
from backend.config import (
    get_db_connection,
    SECRET_KEY,
    WKHTMLTOPDF_PATH,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_SECURE,
    SMTP_USER,
    SMTP_PASS,
    SMTP_FROM,
    param_style,
)
from backend.db import init_db as initialize_database

BASE_DIR = Path(__file__).resolve().parent.parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / 'templates'),
    static_folder=str(BASE_DIR / 'static')
)
app.secret_key = SECRET_KEY

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def send_email(subject: str, body: str, recipient: str):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = recipient
    message.set_content(body)

    if SMTP_SECURE and SMTP_PORT == 465:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

    with server as smtp:
        smtp.ehlo()
        if not (SMTP_SECURE and SMTP_PORT == 465):
            smtp.starttls()
            smtp.ehlo()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(message)


def generate_temp_password(length: int = 10) -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))

def generate_otp(length: int = 6) -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))

# ---------------- DB ----------------
conn = get_db_connection()
initialize_database(conn)
conn.close()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(param_style("SELECT * FROM users WHERE username=? AND password=?"), (u,p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/google-login")
def google_login():
    session["user"] = "naren2004@gmail.com"
    return redirect("/dashboard")

# ---------------- FORGOT PASSWORD ----------------
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    step = "request"
    username = ""

    if request.method == "POST":
        action = request.form.get("action", "request")

        if action == "request":
            username = request.form["username"].strip()

            conn = get_db_connection()
            c = conn.cursor()
            c.execute(param_style("SELECT id, username FROM users WHERE username=?"), (username,))
            user = c.fetchone()

            if user:
                user_id = user[0]
                user_email = user[1]
                otp = generate_otp(6)
                expires_at = datetime.utcnow() + timedelta(minutes=10)

                session["reset_user_id"] = user_id
                session["reset_username"] = user_email
                session["reset_otp"] = otp
                session["reset_otp_expires"] = expires_at.isoformat()
                conn.close()

                email_subject = "Newsletter Portal OTP Verification"
                email_body = (
                    "Hello,\n\n"
                    "A password reset request was received for your account.\n\n"
                    f"Your one-time password (OTP) is: {otp}\n\n"
                    "Enter this code on the website and choose a new password.\n\n"
                    "If you did not request this reset, please contact the system administrator.\n"
                )
                try:
                    send_email(email_subject, email_body, user_email)
                    flash("An OTP has been sent to your email. Use it to set a new password.", "success")
                    step = "verify"
                except Exception as error:
                    flash(f"Unable to send email: {error}", "danger")
                    step = "request"
            else:
                conn.close()
                flash("No account found with that email.", "danger")

        elif action == "verify":
            username = request.form.get("username", "").strip()
            otp = request.form.get("otp", "").strip()
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()

            if not session.get("reset_user_id") or not session.get("reset_otp"):
                flash("Please request a password reset first.", "danger")
                return redirect("/forgot-password")

            expires_at = datetime.fromisoformat(session.get("reset_otp_expires"))
            if datetime.utcnow() > expires_at:
                session.pop("reset_user_id", None)
                session.pop("reset_username", None)
                session.pop("reset_otp", None)
                session.pop("reset_otp_expires", None)
                flash("Your OTP has expired. Please request a new one.", "danger")
                return redirect("/forgot-password")

            if otp != session.get("reset_otp"):
                flash("Invalid OTP. Please check your email and try again.", "danger")
                step = "verify"
            elif new_password != confirm_password:
                flash("Passwords do not match. Please try again.", "danger")
                step = "verify"
            elif not new_password:
                flash("Please enter a new password.", "danger")
                step = "verify"
            else:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(param_style("UPDATE users SET password=? WHERE id=?"), (new_password, session["reset_user_id"]))
                conn.commit()
                conn.close()

                session.pop("reset_user_id", None)
                session.pop("reset_username", None)
                session.pop("reset_otp", None)
                session.pop("reset_otp_expires", None)

                flash("Password changed successfully. Please log in with your new password.", "success")
                return redirect("/")

            username = session.get("reset_username", username)

    elif session.get("reset_user_id") and session.get("reset_otp"):
        step = "verify"
        username = session.get("reset_username", "")

    return render_template("forgot_password.html", step=step, username=username)

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("SELECT * FROM newsletters"))
    data = c.fetchall()
    conn.close()

    return render_template("dashboard.html", data=data)

# ---------------- EDITOR ----------------
@app.route("/editor", methods=["GET","POST"])
def editor():
    if "user" not in session:
        return redirect("/")
        
    if request.method == "POST":
        month = request.form.get("month", "")
        year = request.form.get("year", "")
        chairman = request.form.get("chairman", "")
        principal = request.form.get("principal", "")
        contents = request.form.get("contents", "")
        events = request.form.get("events", "")
        training = request.form.get("training", "")
        workshop = request.form.get("workshop", "")
        achievements = request.form.get("achievements", "")
        seminar = request.form.get("seminar", "")
        faculty = request.form.get("faculty", "")
        dakshaa = request.form.get("dakshaa", "")
        guest = request.form.get("guest", "")
        celebration = request.form.get("celebration", "")
        summary = request.form.get("summary", "")
        editorial = request.form.get("editorial", "")
        last_quote = request.form.get("last_quote", "")

        file = request.files.get("image")
        img_path = ""
        if file and file.filename:
            img_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(img_path)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(param_style(
            "INSERT INTO newsletters(`month`, `year`, `chairman`, `principal`, `contents`, `events`, `training`, `workshop`, `achievements`, `seminar`, `faculty`, `dakshaa`, `guest`, `celebration`, `editorial`, `summary`, `last_quote`, `image`, `created_by`) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        ),
        (month, year, chairman, principal, contents, events, training, workshop, achievements,
         seminar, faculty, dakshaa, guest, celebration, editorial, summary, last_quote, img_path, session["user"]))
        conn.commit()
        conn.close()
        flash('Newsletter created successfully!', 'success')
        return redirect("/dashboard")

    return render_template("editor.html")

# ---------------- ADD USER ----------------
@app.route("/add-user", methods=["GET","POST"])
def add_user():
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    c = conn.cursor()

    if request.method == "POST":
        action = request.form.get("action", "create")
        if action == "create":
            username = request.form["username"]
            password = request.form["password"]
            role = request.form["role"]
            c.execute(param_style("INSERT INTO users VALUES(NULL,?,?,?)"), (username, password, role))
            conn.commit()
            flash('User created successfully!', 'success')
        elif action == "delete":
            user_id = request.form["user_id"]
            c.execute(param_style("DELETE FROM users WHERE id=?"), (user_id,))
            conn.commit()
            flash('User deleted successfully!', 'success')
        elif action == "reset_password":
            user_id = request.form["user_id"]
            default_password = "123456"
            c.execute(param_style("UPDATE users SET password=? WHERE id=?"), (default_password, user_id))
            conn.commit()
            flash('Password reset successfully! New password is 123456', 'success')
        elif action == "change_role":
            user_id = request.form["user_id"]
            role = request.form["role"]
            c.execute(param_style("UPDATE users SET role=? WHERE id=?"), (role, user_id))
            conn.commit()
            flash('User role updated successfully!', 'success')

    c.execute(param_style("SELECT id, username, role FROM users"))
    users = c.fetchall()
    conn.close()

    return render_template("add_user.html", users=users)

@app.route("/delete-user/<int:user_id>")
def delete_user(user_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("DELETE FROM users WHERE id=?"), (user_id,))
    conn.commit()
    conn.close()
    flash('User deleted successfully!', 'success')
    return redirect('/add-user')

@app.route("/reset-password/<int:user_id>")
def reset_password(user_id):
    if "user" not in session:
        return redirect("/")

    default_password = "123456"
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("UPDATE users SET password=? WHERE id=?"), (default_password, user_id))
    conn.commit()
    conn.close()
    flash('Password reset successfully! New password is 123456', 'success')
    return redirect('/add-user')

@app.route("/change-role/<int:user_id>")
def change_role(user_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("SELECT role FROM users WHERE id=?"), (user_id,))
    existing = c.fetchone()
    if existing:
        new_role = "admin" if existing[0] != "admin" else "user"
        c.execute(param_style("UPDATE users SET role=? WHERE id=?"), (new_role, user_id))
        conn.commit()
    conn.close()
    flash('User role updated successfully!', 'success')
    return redirect('/add-user')

@app.route("/edit-user/<int:user_id>", methods=["GET","POST"])
def edit_user(user_id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    c = conn.cursor()

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form["role"]
        c.execute(param_style("UPDATE users SET username=?, password=?, role=? WHERE id=?"),
                  (username, password, role, user_id))
        conn.commit()
        conn.close()
        flash('User updated successfully!', 'success')
        return redirect('/add-user')

    c.execute(param_style("SELECT id, username, password, role FROM users WHERE id=?"), (user_id,))
    edit_user = c.fetchone()
    c.execute(param_style("SELECT id, username, role FROM users"))
    users = c.fetchall()
    conn.close()

    return render_template("add_user.html", users=users, edit_user=edit_user)

# ---------------- PDF DOWNLOAD ----------------
@app.route("/pdf/<int:id>")
def pdf(id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("SELECT * FROM newsletters WHERE id=?"), (id,))
    data = c.fetchone()
    conn.close()

    html = render_template("template_base.html", data=data)
    config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
    pdf_bytes = pdfkit.from_string(
        html,
        False,
        configuration=config,
        options={"enable-local-file-access": None}
    )

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        download_name=f"newsletter_{id}.pdf",
        as_attachment=True,
    )

# ---------------- EDIT NEWSLETTER ----------------
@app.route("/edit/<int:id>", methods=["GET","POST"])
def edit_newsletter(id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    c = conn.cursor()

    if request.method == "POST":
        month = request.form.get("month", "")
        year = request.form.get("year", "")
        chairman = request.form.get("chairman", "")
        principal = request.form.get("principal", "")
        contents = request.form.get("contents", "")
        events = request.form.get("events", "")
        training = request.form.get("training", "")
        workshop = request.form.get("workshop", "")
        achievements = request.form.get("achievements", "")
        seminar = request.form.get("seminar", "")
        faculty = request.form.get("faculty", "")
        dakshaa = request.form.get("dakshaa", "")
        guest = request.form.get("guest", "")
        celebration = request.form.get("celebration", "")
        summary = request.form.get("summary", "")
        editorial = request.form.get("editorial", "")
        last_quote = request.form.get("last_quote", "")

        file = request.files.get("image")
        img_path = ""
        
        # Get existing image path if no new image uploaded
        c.execute(param_style("SELECT image FROM newsletters WHERE id=?"), (id,))
        existing = c.fetchone()
        if existing:
            img_path = existing[0]
        
        if file and file.filename:
            img_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(img_path)

        c.execute(param_style(
            "UPDATE newsletters SET `month`=?, `year`=?, `chairman`=?, `principal`=?, `contents`=?, `events`=?, `training`=?, `workshop`=?, `achievements`=?, `seminar`=?, `faculty`=?, `dakshaa`=?, `guest`=?, `celebration`=?, `editorial`=?, `summary`=?, `last_quote`=?, `image`=? WHERE id=?"
        ),
        (month, year, chairman, principal, contents, events, training, workshop, achievements,
         seminar, faculty, dakshaa, guest, celebration, editorial, summary, last_quote, img_path, id))
        conn.commit()
        conn.close()
        flash('Newsletter updated successfully!', 'success')
        return redirect("/dashboard")

    c.execute(param_style("SELECT * FROM newsletters WHERE id=?"), (id,))
    newsletter = c.fetchone()
    conn.close()

    if not newsletter:
        flash('Newsletter not found!', 'danger')
        return redirect("/dashboard")

    return render_template("editor.html", edit_mode=True, data=newsletter)

# ---------------- DELETE NEWSLETTER ----------------
@app.route("/delete/<int:id>")
def delete_newsletter(id):
    if "user" not in session:
        return redirect("/")

    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("DELETE FROM newsletters WHERE id=?"), (id,))
    conn.commit()
    conn.close()
    
    flash('Newsletter deleted successfully!', 'success')
    return redirect("/dashboard")

# ---------------- LOGOUT ----------------
@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)