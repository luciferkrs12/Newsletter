import threading
import time
from pathlib import Path

import requests
import streamlit as st

from backend.app import app as flask_app

FLASK_PORT = 8502
FLASK_URL = f"http://127.0.0.1:{FLASK_PORT}"


def run_flask():
    flask_app.run(host="127.0.0.1", port=FLASK_PORT, debug=False, use_reloader=False)


if "flask_thread" not in st.session_state:
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    st.session_state["flask_thread"] = flask_thread
    time.sleep(1)

# Wait for Flask backend to be ready
for _ in range(10):
    try:
        requests.get(FLASK_URL, timeout=1)
        break
    except requests.RequestException:
        time.sleep(0.5)

st.title("Newsletter Portal — Streamlit Host")
st.markdown(
    "Use this Streamlit wrapper to host the existing newsletter Flask application inside a local Streamlit UI. "
    "The dashboard, editor, and PDF export pages are served from the embedded Flask app."
)

st.markdown("**How to use:** Open the app below, log in with your account, and use the newsletter editor normally.")

st.components.v1.iframe(FLASK_URL, height=1200, scrolling=True)

st.markdown(
    "---\n"
    "**Note:** This wrapper launches the Flask backend locally on port 8502 and embeds it inside Streamlit. "
    "Run with `streamlit run streamlit_app.py`."
)
