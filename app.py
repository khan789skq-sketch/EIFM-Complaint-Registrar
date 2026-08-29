from pathlib import Path
from datetime import date, time, datetime
import hashlib
import secrets
import sqlite3

import openpyxl
import streamlit as st

from generate_sheet import (
    EQUIPMENT_SHEETS,
    create_ppm_from_template,
    create_wcc_from_template,
    read_template_tasks,
    WCC_TEMPLATE,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS = BASE_DIR / "outputs"
DB_PATH = BASE_DIR / "eifm_app.db"
LOGO = BASE_DIR / "EIFM_logo.jpg"
OUTPUTS.mkdir(exist_ok=True)

st.set_page_config(page_title="EIFM WCC & PPM", page_icon="📋", layout="wide")

st.markdown("""
<style>
.stApp { background: linear-gradient(135deg,#07151a 0%,#101c22 55%,#07151a 100%); }
[data-testid="stSidebar"] { background:#0b151a; }
.block-container { padding-top:1.2rem; padding-bottom:2rem; }
.eifm-card { padding:18px; border-radius:14px; border:1px solid rgba(255,255,255,.10); background:rgba(255,255,255,.035); margin-bottom:14px; }
.small-muted { color:#9aa9af; font-size:.88rem; }
</style>
""", unsafe_allow_html=True)


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        email TEXT PRIMARY KEY, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT NOT NULL, kind TEXT NOT NULL,
        project TEXT, equipment TEXT, number TEXT, created_at TEXT NOT NULL, file_path TEXT)""")
    conn.commit()
    return conn


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 200000)
    return salt.hex() + "$" + digest.hex()


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        got = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 200000)
        return secrets.compare_digest(got.hex(), digest_hex)
    except Exception:
        return False


def authenticate(email, password):
    with db() as conn:
        row = conn.execute("SELECT password_hash FROM users WHERE email=?", (email.strip().lower(),)).fetchone()
    return bool(row and verify_password(password, row["password_hash"]))


def create_user(email, password):
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Enter a valid email."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    try:
        with db() as conn:
            conn.execute("INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
                         (email, hash_password(password), datetime.now().isoformat(timespec="seconds")))
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."


def add_record(kind, project, equipment, number, file_path):
    with db() as conn:
        conn.execute("""INSERT INTO records(email,kind,project,equipment,number,created_at,file_path)
                       VALUES(?,?,?,?,?,?,?)""",
                     (st.session_state.user, kind, project, equipment, number,
                      datetime.now().isoformat(timespec="seconds"), str(file_path)))


def get_records():
    with db() as conn:
        return conn.execute("SELECT * FROM records WHERE email=? ORDER BY id DESC",
                            (st.session_state.user,)).fetchall()


def safe_name(text):
    text = str(text or "").strip()
    return "".join(ch if ch.isalnum() or ch in "-_ ." else "_" for ch in text).replace(" ", "_") or "Document"


def checklist_editor(equipment):
    template_tasks = read_template_tasks(equipment)
    if not template_tasks:
        st.warning("No checklist rows were found in this equipment sheet.")
        return [], {}, {}, {}
    st.info("Checklist is loaded directly from the selected original Excel worksheet.")
    tasks_text = st.text_area("Service Specification Tasks (one per line)", "\n".join(template_tasks), height=240)
    tasks = [x.strip() for x in tasks_text.splitlines() if x.strip()]
    statuses, remarks, followups = {}, {}, {}
    for i, task in enumerate(tasks, 1):
        c1, c2, c3, c4 = st.columns([5, 1, 1, 3])
        with c1:
            st.write(f"{i}. {task}")
        with c2:
            statuses[i] = st.checkbox("OK", key=f"ok_{equipment}_{i}")
        with c3:
            statuses[f"no_{i}"] = st.checkbox("Not OK", key=f"no_{equipment}_{i}")
        with c4:
            remarks[i] = st.text_input("Remarks", key=f"rem_{equipment}_{i}", label_visibility="collapsed")
            followups[i] = st.text_input("Follow-up WO", key=f"fol_{equipment}_{i}", label_visibility="collapsed")
    return tasks, statuses, remarks, followups


if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("EIFM WCC & PPM")
    if LOGO.exists():
        st.image(str(LOGO), width=140)
    st.caption("EIFM PPM & WCC Generator")
    tab1, tab2 = st.tabs(["Sign in", "Sign up"])
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Sign in", type="primary", use_container_width=True):
            if authenticate(email, password):
                st.session_state.user = email.strip().lower()
                st.rerun()
            else:
                st.error("Email or password is incorrect.")
    with tab2:
        email2 = st.text_input("Email", key="signup_email")
        p1 = st.text_input("Password", type="password", key="signup_p1")
        p2 = st.text_input("Confirm password", type="password", key="signup_p2")
        if st.button("Create account", use_container_width=True):
            if p1 != p2:
                st.error("Passwords do not match.")
            else:
                ok, msg = create_user(email2, p1)
                (st.success if ok else st.error)(msg)
    st.stop()

with st.sidebar:
    if LOGO.exists():
        st.image(str(LOGO), width=95)
    st.markdown("### EIFM WCC & PPM")
    st.caption(st.session_state.user)
    page = st.radio("Menu", ["Dashboard", "New PPM", "New WCC", "My Records"])
    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

if page == "Dashboard":
    records = get_records()
    st.title("📋 EIFM WCC & PPM Generator")
    st.markdown('<div class="eifm-card"><h3>Original templates are used</h3>'
                '<div class="small-muted">PPM uses the supplied Excel worksheets. WCC uses the supplied EIFMEN08 Word template.</div></div>', unsafe_allow_html=True)
    a,b,c = st.columns(3)
    a.metric("My Records", len(records))
    b.metric("Equipment Templates", len(EQUIPMENT_SHEETS))
    c.metric("PPM Excel Templates", 2)
    st.subheader("PPM")
    st.write("Planned Preventive Maintenance Service Complete as per Attached Check List")
    st.write("PPM Number: 1st PPM / 2nd PPM / 3rd PPM / 4th PPM")
    st.subheader("Equipment worksheets")
    st.write(", ".join(EQUIPMENT_SHEETS) if EQUIPMENT_SHEETS else "No Excel templates found.")

elif page == "New PPM":
    st.title("🛠️ New PPM Task Sheet")
    if not EQUIPMENT_SHEETS:
        st.error("All.xlsx / All-3.xlsx could not be found in the application root.")
        st.stop()
    with st.form("ppm_form"):
        c1,c2 = st.columns(2)
        with c1:
            project = st.text_input("Project Name")
            location = st.text_input("Location")
            unit = st.text_input("Unit Number")
            frequency = st.selectbox("Frequency", ["Monthly", "Quarterly", "Semi-Annual", "Annual", "Corrective / Complaint"])
            category = st.text_input("Category")
            equipment = st.selectbox("Equipment", EQUIPMENT_SHEETS)
        with c2:
            fiscal_year = st.number_input("Fiscal Year", min_value=2000, max_value=2100, value=date.today().year)
            wo = st.text_input("WO Number")
            ppm_number = st.selectbox("PPM Number", ["1st PPM", "2nd PPM", "3rd PPM", "4th PPM"])
            month = st.selectbox("Scheduled Month", ["January","February","March","April","May","June","July","August","September","October","November","December"], index=date.today().month-1)
            service_date = st.date_input("Date of Service", date.today())
            start = st.time_input("Time Start", time(8,0))
            finish = st.time_input("Time Finish", time(17,0))
        st.markdown("**Details Of Work**")
        st.info("Planned Preventive Maintenance Service Complete as per Attached Check List")
        tasks, statuses, remarks, followups = checklist_editor(equipment)
        technician = st.text_input("Tech. Date/Sign")
        engineer = st.text_input("Eng./Sup Date Sign")
        summary = st.text_area("REPORT SUMMARY", height=100)
        generate = st.form_submit_button("Generate PPM Excel", type="primary", use_container_width=True)
    if generate:
        if not project.strip():
            st.error("Project Name is required.")
        else:
            out = OUTPUTS / f"PPM_{safe_name(equipment)}_{safe_name(ppm_number)}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
            try:
                create_ppm_from_template(
                    equipment, project, location, unit, frequency, category, fiscal_year,
                    wo, ppm_number, month, service_date.strftime("%d/%m/%Y"),
                    start.strftime("%H:%M"), finish.strftime("%H:%M"),
                    tasks, statuses, remarks, followups, technician, engineer, summary, out
                )
                add_record("PPM", project, equipment, ppm_number, out)
                st.success("PPM Excel generated successfully using the original equipment worksheet.")
                st.download_button("📥 Download PPM Excel", out.read_bytes(), out.name,
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            except Exception as exc:
                st.exception(exc)

elif page == "New WCC":
    st.title("📄 New Work Completion Certificate")
    st.caption("The supplied EIFMEN08 Word document is used as the base template.")
    if not WCC_TEMPLATE.exists():
        st.error(f"WCC template not found: {WCC_TEMPLATE.name}")
        st.stop()
    with st.form("wcc_form"):
        c1,c2 = st.columns(2)
        with c1:
            job = st.text_input("Job Order Number")
            client = st.text_input("Client")
            project = st.text_input("Project")
            location = st.text_input("Location")
            tel = st.text_input("Tel. No.")
            details = st.text_area("Details of Work", height=170)
            completion = st.text_input("Date & Time of Completion")
            site_sig = st.text_input("Signature of Site in Charge")
            site_name = st.text_input("Site in Charge Name")
            site_date = st.text_input("Site in Charge Date")
            site_id = st.text_input("Site in Charge ID")
        with c2:
            hod_sig = st.text_input("Signature of HOD")
            hod_name = st.text_input("HOD Name")
            hod_date = st.text_input("HOD Date")
            hod_id = st.text_input("HOD ID")
            client_sig = st.text_input("Client Signature")
            client_name = st.text_input("Client Name")
            client_phone = st.text_input("Client Phone No.")
            satisfaction = st.selectbox("Satisfaction", ["1. Poor", "2. Satisfied", "3. Good", "4. Very Good", "5. Excellent"])
            client_sign_date = st.text_input("Client Signature Date")
            remarks_wcc = st.text_area("Remarks / Suggestions", height=100)
        docs = st.multiselect("Select enclosed documents",
            ["LPO", "Invoice", "Delivery Note", "Petty Cash", "Material Requisition", "Job Completion"],
            default=["Job Completion"])
        generate = st.form_submit_button("Generate WCC", type="primary", use_container_width=True)
    if generate:
        if not job.strip() or not client.strip() or not project.strip():
            st.error("Job Order Number, Client and Project are required.")
        else:
            out = OUTPUTS / f"WCC_{safe_name(job)}_{datetime.now():%Y%m%d_%H%M%S}.docx"
            try:
                create_wcc_from_template(
                    job, client, project, location, tel, details, completion,
                    site_sig, site_name, site_date, site_id,
                    hod_sig, hod_name, hod_date, hod_id,
                    docs, client_sig, client_name, client_phone, satisfaction,
                    remarks_wcc, client_sign_date, out
                )
                add_record("WCC", project, "", job, out)
                st.success("WCC generated successfully using the supplied EIFMEN08 template.")
                st.download_button("📥 Download WCC Word", out.read_bytes(), out.name,
                                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            except Exception as exc:
                st.exception(exc)

else:
    st.title("📚 My Records")
    rows = get_records()
    if not rows:
        st.info("No records yet.")
    for row in rows:
        p = Path(row["file_path"])
        with st.expander(f'{row["kind"]} | {row["project"] or "-"} | {row["number"] or "-"} | {row["created_at"]}'):
            st.write("Equipment:", row["equipment"] or "-")
            if p.exists():
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if p.suffix.lower()==".xlsx" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                st.download_button("📥 Download", p.read_bytes(), p.name, mime, key=f"download_{row['id']}")
            else:
                st.warning("Generated file is no longer present on this server instance.")
