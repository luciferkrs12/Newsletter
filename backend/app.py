from flask import Flask, render_template, request, redirect, session, send_file, flash
import os
from pathlib import Path
import pdfkit
from backend.config import get_db_connection, SECRET_KEY, WKHTMLTOPDF_PATH, param_style
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
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        file = request.files["image"]
        img_path = ""
        if file:
            img_path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(img_path)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(param_style("INSERT INTO newsletters VALUES(NULL,?,?,?)"),
                  (title, content, img_path))
        conn.commit()
        conn.close()

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
    pdfkit.from_string(html, "output.pdf", configuration=config)

    return send_file("output.pdf")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)