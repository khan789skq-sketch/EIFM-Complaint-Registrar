import base64
import hashlib
import hmac
import os
import secrets
import smtplib
import sqlite3
from datetime import date, datetime, timedelta, time
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components

from generate_sheet import (
    EQUIPMENT_SHEETS,
    create_ppm_from_template,
    create_wcc_from_template,
    read_template_tasks,
)

# ============================================================
# EIFM WCC & PPM — upgraded Streamlit application
# Keeps the supplied Excel/Word template generators intact.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = BASE_DIR / "templates"

# Supports both the original /assets layout and the logo at repo root.
ASSET_DIRS = [BASE_DIR / "assets", BASE_DIR]
OUTPUTS = BASE_DIR / "outputs"
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.getenv("EIFM_DB_PATH", str(DATA_DIR / "eifm_app.db")))

OUTPUTS.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

APP_NAME = "EIFM WCC & PPM"
GREEN = "#159447"
DARK = "#0b1f17"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def find_logo():
    for folder in ASSET_DIRS:
        for name in ("EIFM_logo.png", "EIFM_logo.jpg", "EIFM_logo.jpeg", "logo.png", "logo.jpg"):
            p = folder / name
            if p.exists():
                return p
    return None

LOGO = find_logo()

def logo_data_uri():
    if not LOGO:
        return ""
    mime = "image/png" if LOGO.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(LOGO.read_bytes()).decode()}"

LOGO_URI = logo_data_uri()

# ---------------- Theme / responsive UI ----------------
st.markdown(f"""
<style>
:root {{
  --eifm-green: {GREEN};
  --eifm-dark: {DARK};
  --eifm-soft: #eef8f2;
  --eifm-border: #dce9e1;
}}
.stApp {{
  background:
    radial-gradient(circle at 90% 0%, rgba(21,148,71,.10), transparent 30%),
    linear-gradient(180deg, #ffffff 0%, #ffffff 70%, #f0f8f3 100%);
}}
[data-testid="stHeader"] {{ background: rgba(255,255,255,.92); }}
.block-container {{ max-width: 1180px; padding-top: 1rem; padding-bottom: 3rem; }}
h1,h2,h3,h4 {{ color: #10251b; }}
.eifm-top {{
  display:flex; align-items:center; justify-content:space-between; gap:16px;
  padding:14px 18px; border-radius:18px; background:#fff;
  border:1px solid var(--eifm-border); box-shadow:0 8px 28px rgba(16,37,27,.07);
  margin-bottom:18px;
}}
.eifm-brand {{ display:flex; align-items:center; gap:12px; }}
.eifm-brand img {{ width:52px; height:52px; object-fit:contain; border-radius:12px; }}
.eifm-brand-title {{ font-weight:800; font-size:1.05rem; color:#10251b; }}
.eifm-brand-sub {{ color:#718077; font-size:.78rem; }}
.hero {{
  border-radius:24px; padding:24px; color:white; overflow:hidden;
  background:
    linear-gradient(120deg, rgba(9,54,34,.96), rgba(21,148,71,.88)),
    #159447;
  box-shadow:0 16px 42px rgba(9,54,34,.16);
  margin-bottom:18px;
}}
.hero-row {{ display:flex; align-items:center; justify-content:space-between; gap:20px; }}
.hero h1 {{ color:white; margin:0 0 6px 0; font-size:clamp(1.65rem,4vw,2.35rem); }}
.hero p {{ margin:0; color:rgba(255,255,255,.82); }}
.hero img {{ width:94px; height:94px; object-fit:contain; background:rgba(255,255,255,.96); border-radius:20px; padding:8px; }}
.card {{
  background:#fff; border:1px solid var(--eifm-border); border-radius:18px;
  padding:18px; min-height:132px; box-shadow:0 8px 24px rgba(16,37,27,.05);
}}
.card-title {{ font-weight:800; font-size:1.05rem; color:#10251b; }}
.card-sub {{ color:#718077; font-size:.84rem; margin-top:4px; }}
.metric {{
  background:#fff; border:1px solid var(--eifm-border); border-radius:16px;
  padding:14px 16px;
}}
.metric-number {{ font-size:1.55rem; font-weight:800; color:var(--eifm-green); }}
.section {{
  background:#fff; border:1px solid var(--eifm-border); border-radius:18px;
  padding:18px; margin:16px 0;
}}
.badge {{
 display:inline-block; padding:4px 9px; border-radius:999px;
 background:#eaf7ef; color:#11723b; font-size:.75rem; font-weight:700;
}}
.stButton > button {{
  border-radius:12px !important; min-height:44px !important; font-weight:700 !important;
}}
.stDownloadButton > button {{ border-radius:12px !important; }}
[data-testid="stSidebar"] {{
  background:#0b1f17;
}}
[data-testid="stSidebar"] * {{ color:white !important; }}
@media (max-width: 700px) {{
  .block-container {{ padding-left: .8rem; padding-right: .8rem; }}
  .hero {{ padding:18px; border-radius:20px; }}
  .hero img {{ width:70px; height:70px; }}
  .eifm-top {{ padding:10px 12px; }}
}}
</style>
""", unsafe_allow_html=True)

def render_brand():
    if LOGO_URI:
        st.markdown(
            f'<div class="eifm-top"><div class="eifm-brand">'
            f'<img src="{LOGO_URI}"><div><div class="eifm-brand-title">{APP_NAME}</div>'
            f'<div class="eifm-brand-sub">Work Completion Certificate & Preventive Maintenance</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="eifm-top"><div class="eifm-brand">'
            f'<div><div class="eifm-brand-title">{APP_NAME}</div>'
            f'<div class="eifm-brand-sub">Work Completion Certificate & Preventive Maintenance</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

# ---------------- Database ----------------
def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            kind TEXT NOT NULL,
            project TEXT,
            equipment TEXT,
            number TEXT,
            created_at TEXT NOT NULL,
            ppm_file TEXT,
            wcc_file TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reset_tokens (
            email TEXT PRIMARY KEY,
            token_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn

def password_hash(password):
    # PBKDF2 is used for new passwords; legacy SHA-256 hashes are still accepted.
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000)
    return "pbkdf2$180000$" + base64.urlsafe_b64encode(salt).decode() + "$" + base64.urlsafe_b64encode(digest).decode()

def verify_password(stored, password):
    if stored.startswith("pbkdf2$"):
        try:
            _, rounds, salt_b64, digest_b64 = stored.split("$", 3)
            salt = base64.urlsafe_b64decode(salt_b64.encode())
            expected = base64.urlsafe_b64decode(digest_b64.encode())
            actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False
    return hmac.compare_digest(stored, hashlib.sha256(password.encode("utf-8")).hexdigest())

def authenticate(email, password):
    conn = db()
    row = conn.execute("SELECT email,password_hash FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    if not row:
        conn.close()
        return False
    ok = verify_password(row[1], password)
    if ok and not row[1].startswith("pbkdf2$"):
        conn.execute("UPDATE users SET password_hash=? WHERE email=?", (password_hash(password), row[0]))
        conn.commit()
    conn.close()
    return ok

def create_user(email, password):
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Enter a valid email."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    conn = db()
    try:
        conn.execute(
            "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            (email, password_hash(password), datetime.now().isoformat(timespec="seconds"))
        )
        conn.commit()
        return True, "Account created. You can sign in now."
    except sqlite3.IntegrityError:
        return False, "This email is already registered. Use Forgot Password if you forgot it."
    finally:
        conn.close()

def issue_reset_token(email):
    email = email.strip().lower()
    conn = db()
    exists = conn.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone()
    if not exists:
        conn.close()
        return None
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = (datetime.utcnow() + timedelta(minutes=30)).isoformat()
    conn.execute(
        "INSERT INTO reset_tokens(email,token_hash,expires_at) VALUES(?,?,?) "
        "ON CONFLICT(email) DO UPDATE SET token_hash=excluded.token_hash,expires_at=excluded.expires_at",
        (email, token_hash, expires)
    )
    conn.commit()
    conn.close()
    return token

def send_reset_email(email, token):
    host = os.getenv("EIFM_SMTP_HOST")
    port = int(os.getenv("EIFM_SMTP_PORT", "587"))
    username = os.getenv("EIFM_SMTP_USERNAME")
    password = os.getenv("EIFM_SMTP_PASSWORD")
    sender = os.getenv("EIFM_SMTP_FROM", username or "")
    app_url = os.getenv("EIFM_APP_URL", "")
    if not all([host, username, password, sender, app_url]):
        return False, "Email reset is not configured yet. Add EIFM_SMTP_* and EIFM_APP_URL secrets."
    reset_url = app_url.rstrip("/") + "?reset=" + quote(token)
    msg = EmailMessage()
    msg["Subject"] = "EIFM WCC & PPM — Password Reset"
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(
        f"Use this link to reset your EIFM password:\n\n{reset_url}\n\n"
        "The link expires in 30 minutes. If you did not request this, ignore the email."
    )
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(msg)
        return True, "Reset link sent. Check your email."
    except Exception:
        return False, "Could not send the reset email. Check SMTP settings."

def reset_password(token, new_password):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = db()
    row = conn.execute(
        "SELECT email,expires_at FROM reset_tokens WHERE token_hash=?",
        (token_hash,)
    ).fetchone()
    if not row or datetime.fromisoformat(row[1]) < datetime.utcnow():
        conn.close()
        return False, "Reset link is invalid or expired."
    if len(new_password) < 8:
        conn.close()
        return False, "Password must be at least 8 characters."
    conn.execute("UPDATE users SET password_hash=? WHERE email=?", (password_hash(new_password), row[0]))
    conn.execute("DELETE FROM reset_tokens WHERE email=?", (row[0],))
    conn.commit()
    conn.close()
    return True, "Password changed successfully. You can sign in now."

def add_record(kind, project, equipment, number, ppm_file="", wcc_file=""):
    conn = db()
    conn.execute(
        """INSERT INTO records(email,kind,project,equipment,number,created_at,ppm_file,wcc_file)
           VALUES(?,?,?,?,?,?,?,?)""",
        (st.session_state.user, kind, project, equipment, number,
         datetime.now().isoformat(timespec="seconds"), ppm_file, wcc_file)
    )
    conn.commit()
    conn.close()

def get_records():
    conn = db()
    rows = conn.execute(
        """SELECT id,kind,project,equipment,number,created_at,ppm_file,wcc_file
           FROM records WHERE email=? ORDER BY id DESC""",
        (st.session_state.user,)
    ).fetchall()
    conn.close()
    return rows

def split_tasks(text):
    return [x.strip() for x in text.splitlines() if x.strip()]

# ---------------- Share helpers ----------------
def share_file_ui(path, title, mime):
    if not path.exists():
        return
    b64 = base64.b64encode(path.read_bytes()).decode()
    safe_name = path.name.replace("\\", "").replace("'", "")
    # Uses the phone/browser Web Share API when supported, including file attachment.
    components.html(f"""
    <div style="font-family:system-ui">
      <button id="share" style="width:100%;padding:12px;border:0;border-radius:10px;background:#159447;color:white;font-weight:700">
        📤 Share {title}
      </button>
      <div id="msg" style="margin-top:8px;font-size:13px;color:#607068"></div>
      <script>
      const data = "{b64}";
      const bytes = Uint8Array.from(atob(data), c => c.charCodeAt(0));
      const blob = new Blob([bytes], {{type: "{mime}"}});
      const file = new File([blob], "{safe_name}", {{type: "{mime}"}});
      document.getElementById("share").onclick = async () => {{
        try {{
          if (navigator.share && (!navigator.canShare || navigator.canShare({{files:[file]}}))) {{
            await navigator.share({{title: "{title}", text: "EIFM WCC & PPM — {safe_name}", files:[file]}});
            document.getElementById("msg").innerText = "Share menu opened.";
          }} else if (navigator.share) {{
            await navigator.share({{title:"{title}", text:"EIFM WCC & PPM — {safe_name}"}});
          }} else {{
            document.getElementById("msg").innerText = "Use Download, then share the file from your phone.";
          }}
        }} catch (e) {{
          document.getElementById("msg").innerText = "Share cancelled or not supported. Use Download.";
        }}
      }};
      </script>
    </div>
    """, height=95)

def quick_share_links(path, title):
    text = quote(f"{title}: {path.name}")
    gmail = f"https://mail.google.com/mail/?view=cm&fs=1&su={quote(title)}&body={text}"
    wa = f"https://wa.me/?text={text}"
    st.markdown(f"**Quick share**  ·  [Gmail]({gmail})  ·  [WhatsApp]({wa})")
    st.caption("Gmail/WhatsApp links open the app/site. For the actual file attachment, use the green Share button above or Download → Share.")

# ---------------- Auth screens ----------------
def auth_screen():
    reset_token = st.query_params.get("reset")
    if reset_token:
        render_brand()
        st.markdown("## 🔐 Reset password")
        with st.form("reset_form"):
            p1 = st.text_input("New password", type="password")
            p2 = st.text_input("Confirm new password", type="password")
            ok = st.form_submit_button("Change password", type="primary", use_container_width=True)
        if ok:
            if p1 != p2:
                st.error("Passwords do not match.")
            else:
                success, msg = reset_password(reset_token, p1)
                (st.success if success else st.error)(msg)
                if success:
                    st.query_params.clear()
        st.stop()

    c1, c2, c3 = st.columns([1, 1.7, 1])
    with c2:
        if LOGO:
            st.image(str(LOGO), width=150)
        st.markdown("## Welcome to EIFM")
        st.caption("Work Completion Certificate & Preventive Maintenance")
        login_tab, signup_tab, forgot_tab = st.tabs(["Sign in", "Create account", "Forgot password"])

        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submit:
                if authenticate(email, password):
                    st.session_state.user = email.strip().lower()
                    st.rerun()
                else:
                    st.error("Email or password is incorrect.")

        with signup_tab:
            with st.form("signup_form"):
                email2 = st.text_input("Email", key="signup_email")
                p1 = st.text_input("Password", type="password", key="signup_p1")
                p2 = st.text_input("Confirm password", type="password", key="signup_p2")
                submit2 = st.form_submit_button("Create account", use_container_width=True)
            if submit2:
                if p1 != p2:
                    st.error("Passwords do not match.")
                else:
                    ok, msg = create_user(email2, p1)
                    (st.success if ok else st.error)(msg)

        with forgot_tab:
            st.info("Enter the email used for your account. A reset link will be sent when email settings are configured.")
            with st.form("forgot_form"):
                email3 = st.text_input("Registered email", key="forgot_email")
                submit3 = st.form_submit_button("Send reset link", type="primary", use_container_width=True)
            if submit3:
                token = issue_reset_token(email3)
                if token:
                    ok, msg = send_reset_email(email3.strip().lower(), token)
                    (st.success if ok else st.error)(msg)
                else:
                    # Do not reveal whether an account exists in a production setup.
                    st.success("If that email is registered, a reset message will be sent.")
    st.stop()

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    auth_screen()

# ---------------- Navigation ----------------
with st.sidebar:
    if LOGO:
        st.image(str(LOGO), width=110)
    st.markdown(f"### {APP_NAME}")
    st.caption(st.session_state.user)
    page = st.radio(
        "Menu",
        ["🏠 Home", "📄 New WCC", "🛠️ New PPM", "📚 My Records", "⚙️ Settings"],
        index=0,
    )
    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# ---------------- Home ----------------
if page == "🏠 Home":
    render_brand()
    records = get_records()
    st.markdown(
        f'<div class="hero"><div class="hero-row"><div>'
        f'<h1>Welcome, {st.session_state.user.split("@")[0]}</h1>'
        f'<p>Create, save, download and share EIFM WCC & PPM documents.</p>'
        f'</div>{f"<img src=\'{LOGO_URI}\'>" if LOGO_URI else ""}</div></div>',
        unsafe_allow_html=True,
    )

    a,b,c,d = st.columns(4)
    with a:
        st.markdown('<div class="metric"><div>My Records</div><div class="metric-number">%s</div></div>' % len(records), unsafe_allow_html=True)
    with b:
        st.markdown('<div class="metric"><div>WCC</div><div class="metric-number">%s</div></div>' % sum(1 for r in records if r[1]=="WCC"), unsafe_allow_html=True)
    with c:
        st.markdown('<div class="metric"><div>PPM</div><div class="metric-number">%s</div></div>' % sum(1 for r in records if r[1]=="PPM"), unsafe_allow_html=True)
    with d:
        st.markdown('<div class="metric"><div>Equipment Templates</div><div class="metric-number">%s</div></div>' % len(EQUIPMENT_SHEETS), unsafe_allow_html=True)

    st.markdown("### Quick actions")
    q1,q2,q3 = st.columns(3)
    with q1:
        st.markdown('<div class="card"><div class="card-title">📄 New WCC</div><div class="card-sub">Create a Work Completion Certificate using the supplied template.</div></div>', unsafe_allow_html=True)
        if st.button("Create WCC", use_container_width=True):
            st.session_state.nav_target = "📄 New WCC"
            st.rerun()
    with q2:
        st.markdown('<div class="card"><div class="card-title">🛠️ New PPM</div><div class="card-sub">Create a Preventive Maintenance sheet from the original Excel equipment template.</div></div>', unsafe_allow_html=True)
        if st.button("Create PPM", use_container_width=True):
            st.session_state.nav_target = "🛠️ New PPM"
            st.rerun()
    with q3:
        st.markdown('<div class="card"><div class="card-title">📚 My Records</div><div class="card-sub">Open, downl
