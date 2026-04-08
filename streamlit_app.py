import streamlit as st
import pandas as pd
from backend.config import get_db_connection, param_style
from backend.db import init_db as initialize_database
import os
from pathlib import Path
import pdfkit
from io import BytesIO
from datetime import datetime, timedelta
import smtplib
import secrets
from email.message import EmailMessage

# Initialize database
conn = get_db_connection()
initialize_database(conn)
conn.close()

# Config
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

from backend.config import (
    WKHTMLTOPDF_PATH,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_SECURE,
    SMTP_USER,
    SMTP_PASS,
    SMTP_FROM,
)

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

def generate_otp(length: int = 6) -> str:
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))

st.set_page_config(page_title="Newsletter Portal", layout="wide")

# Sidebar navigation
if 'user' in st.session_state:
    st.sidebar.title(f"Welcome, {st.session_state['user']}")
    page = st.sidebar.radio("Navigation", ["Dashboard", "Editor", "Add User", "Logout"])
else:
    page = "Login"

if page == "Logout":
    st.session_state.clear()
    st.rerun()

if page == "Login" or 'user' not in st.session_state:
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(param_style("SELECT * FROM users WHERE username=? AND password=?"), (username, password))
            user = c.fetchone()
            conn.close()
            if user:
                st.session_state['user'] = username
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    # Forgot password
    if st.button("Forgot Password?"):
        st.session_state['forgot_step'] = 'request'

    if 'forgot_step' in st.session_state:
        if st.session_state['forgot_step'] == 'request':
            with st.form("forgot_request"):
                email = st.text_input("Enter your email")
                submitted = st.form_submit_button("Send OTP")
                if submitted:
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute(param_style("SELECT id, username FROM users WHERE username=?"), (email,))
                    user = c.fetchone()
                    if user:
                        user_id = user[0]
                        otp = generate_otp(6)
                        expires_at = datetime.utcnow() + timedelta(minutes=10)
                        st.session_state['reset_user_id'] = user_id
                        st.session_state['reset_username'] = email
                        st.session_state['reset_otp'] = otp
                        st.session_state['reset_otp_expires'] = expires_at.isoformat()
                        try:
                            email_subject = "Newsletter Portal OTP Verification"
                            email_body = f"Your OTP is: {otp}"
                            send_email(email_subject, email_body, email)
                            st.success("OTP sent to your email")
                            st.session_state['forgot_step'] = 'verify'
                            st.rerun()
                        except Exception as e:
                            st.error(f"Unable to send email: {e}")
                    else:
                        st.error("No account found with that email")
                    conn.close()

        elif st.session_state['forgot_step'] == 'verify':
            with st.form("forgot_verify"):
                otp_input = st.text_input("Enter OTP")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                submitted = st.form_submit_button("Reset Password")
                if submitted:
                    if datetime.utcnow() > datetime.fromisoformat(st.session_state.get('reset_otp_expires', '')):
                        st.error("OTP expired")
                        del st.session_state['forgot_step']
                        st.rerun()
                    elif otp_input != st.session_state.get('reset_otp'):
                        st.error("Invalid OTP")
                    elif new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute(param_style("UPDATE users SET password=? WHERE id=?"), (new_password, st.session_state['reset_user_id']))
                        conn.commit()
                        conn.close()
                        st.success("Password reset successfully")
                        del st.session_state['forgot_step']
                        del st.session_state['reset_user_id']
                        del st.session_state['reset_username']
                        del st.session_state['reset_otp']
                        del st.session_state['reset_otp_expires']
                        st.rerun()

elif page == "Dashboard":
    st.title("Dashboard")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("SELECT id, month, year, created_by FROM newsletters"))
    data = c.fetchall()
    conn.close()
    if data:
        df = pd.DataFrame(data, columns=["ID", "Month", "Year", "Created By"])
        st.dataframe(df)
        selected = st.selectbox("Select newsletter to view/edit", df["ID"].tolist())
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Download PDF"):
                # PDF download logic
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(param_style("SELECT * FROM newsletters WHERE id=?"), (selected,))
                newsletter_data = c.fetchone()
                conn.close()
                if newsletter_data:
                    html = st.session_state.get('template_html', '<html><body>Newsletter</body></html>')  # Need to load template
                    config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
                    pdf_bytes = pdfkit.from_string(html, False, configuration=config, options={"enable-local-file-access": None})
                    st.download_button("Download PDF", pdf_bytes, f"newsletter_{selected}.pdf", "application/pdf")
        with col2:
            if st.button("Edit"):
                st.session_state['edit_id'] = selected
                st.rerun()
        with col3:
            if st.button("Delete"):
                conn = get_db_connection()
                c = conn.cursor()
                c.execute(param_style("DELETE FROM newsletters WHERE id=?"), (selected,))
                conn.commit()
                conn.close()
                st.success("Deleted")
                st.rerun()
    else:
        st.write("No newsletters yet")

elif page == "Editor":
    st.title("Newsletter Editor")
    edit_id = st.session_state.get('edit_id')
    if edit_id:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(param_style("SELECT * FROM newsletters WHERE id=?"), (edit_id,))
        data = c.fetchone()
        conn.close()
        if data:
            # Pre-fill form with data
            default_month = data[1]
            default_year = data[2]
            # etc.
        st.session_state['edit_id'] = None  # Clear after loading

    with st.form("editor_form"):
        month = st.text_input("Month", value=default_month if 'default_month' in locals() else "")
        year = st.text_input("Year")
        chairman = st.text_area("Chairman's Message")
        principal = st.text_area("Principal's Note")
        contents = st.text_area("Contents")
        events = st.text_area("Events")
        training = st.text_area("Training")
        workshop = st.text_area("Workshop")
        achievements = st.text_area("Achievements")
        seminar = st.text_area("Seminar")
        faculty = st.text_area("Faculty")
        dakshaa = st.text_area("Dakshaa")
        guest = st.text_area("Guest")
        celebration = st.text_area("Celebration")
        summary = st.text_area("Summary")
        editorial = st.text_area("Editorial")
        last_quote = st.text_area("Last Quote")
        image = st.file_uploader("Image")
        submitted = st.form_submit_button("Save Newsletter")
        if submitted:
            img_path = ""
            if image:
                img_path = str(UPLOAD_FOLDER / image.name)
                with open(img_path, "wb") as f:
                    f.write(image.getbuffer())
            conn = get_db_connection()
            c = conn.cursor()
            if edit_id:
                c.execute(param_style(
                    "UPDATE newsletters SET month=?, year=?, chairman=?, principal=?, contents=?, events=?, training=?, workshop=?, achievements=?, seminar=?, faculty=?, dakshaa=?, guest=?, celebration=?, editorial=?, summary=?, last_quote=?, image=? WHERE id=?"
                ), (month, year, chairman, principal, contents, events, training, workshop, achievements, seminar, faculty, dakshaa, guest, celebration, editorial, summary, last_quote, img_path, edit_id))
            else:
                c.execute(param_style(
                    "INSERT INTO newsletters(month, year, chairman, principal, contents, events, training, workshop, achievements, seminar, faculty, dakshaa, guest, celebration, editorial, summary, last_quote, image, created_by) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
                ), (month, year, chairman, principal, contents, events, training, workshop, achievements, seminar, faculty, dakshaa, guest, celebration, editorial, summary, last_quote, img_path, st.session_state['user']))
            conn.commit()
            conn.close()
            st.success("Saved successfully!")
            st.rerun()

elif page == "Add User":
    st.title("User Management")
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(param_style("SELECT id, username, role FROM users"))
    users = c.fetchall()
    conn.close()
    if users:
        df = pd.DataFrame(users, columns=["ID", "Username", "Role"])
        st.dataframe(df)
        selected_user = st.selectbox("Select user", [f"{u[0]} - {u[1]}" for u in users])
        if selected_user:
            user_id = int(selected_user.split(" - ")[0])
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Delete User"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute(param_style("DELETE FROM users WHERE id=?"), (user_id,))
                    conn.commit()
                    conn.close()
                    st.success("Deleted")
                    st.rerun()
            with col2:
                if st.button("Reset Password"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute(param_style("UPDATE users SET password='123456' WHERE id=?"), (user_id,))
                    conn.commit()
                    conn.close()
                    st.success("Password reset to 123456")
            with col3:
                if st.button("Toggle Role"):
                    conn = get_db_connection()
                    c = conn.cursor()
                    c.execute(param_style("SELECT role FROM users WHERE id=?"), (user_id,))
                    role = c.fetchone()[0]
                    new_role = "admin" if role == "user" else "user"
                    c.execute(param_style("UPDATE users SET role=? WHERE id=?"), (new_role, user_id))
                    conn.commit()
                    conn.close()
                    st.success(f"Role changed to {new_role}")

    with st.form("add_user_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        role = st.selectbox("Role", ["user", "admin"])
        submitted = st.form_submit_button("Add User")
        if submitted:
            conn = get_db_connection()
            c = conn.cursor()
            c.execute(param_style("INSERT INTO users(username, password, role) VALUES(?,?,?)"), (username, password, role))
            conn.commit()
            conn.close()
            st.success("User added")
            st.rerun()
