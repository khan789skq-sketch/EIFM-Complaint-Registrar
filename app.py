
import os
import hashlib
import sqlite3
from datetime import date, datetime, time
from pathlib import Path

import streamlit as st

from generate_sheet import (
    EQUIPMENT_SHEETS,
    create_ppm_from_template,
    create_wcc_from_template,
)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = BASE_DIR / "templates"
ASSETS = BASE_DIR / "assets"
OUTPUTS = BASE_DIR / "outputs"
DB_PATH = BASE_DIR / "data" / "eifm_app.db"

OUTPUTS.mkdir(exist_ok=True)
DB_PATH.parent.mkdir(exist_ok=True)

st.set_page_config(
    page_title="EIFM WCC & PPM",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- UI ----------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #07151a 0%, #101c22 55%, #07151a 100%);
}
[data-testid="stSidebar"] {
    background: #0b151a;
}
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}
h1,h2,h3 { letter-spacing: .2px; }
.eifm-card {
    padding: 18px;
    border-radius: 14px;
    border: 1px solid rgba(255,255,255,.10);
    background: rgba(255,255,255,.035);
    margin-bottom: 14px;
}
.small-muted { color: #9aa9af; font-size: .88rem; }
</style>
""", unsafe_allow_html=True)

# ---------- Auth ----------
def db():
    conn = sqlite3.connect(DB_PATH)
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
    conn.commit()
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def authenticate(email, password):
    conn = db()
    row = conn.execute(
        "SELECT email FROM users WHERE email=? AND password_hash=?",
        (email.strip().lower(), hash_password(password))
    ).fetchone()
    conn.close()
    return row is not None

def create_user(email, password):
    email = email.strip().lower()
    if not email or "@" not in email:
        return False, "Enter a valid email."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    conn = db()
    try:
        conn.execute(
            "INSERT INTO users(email,password_hash,created_at) VALUES(?,?,?)",
            (email, hash_password(password), datetime.now().isoformat(timespec="seconds"))
        )
        conn.commit()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "This email is already registered."
    finally:
        conn.close()

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        logo = ASSETS / "EIFM_logo.jpg"
        if logo.exists():
            st.image(str(logo), width=130)
        st.title("EIFM WCC & PPM")
        st.caption("Work Completion Certificate & Preventive Maintenance")

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

# ---------- Helpers ----------
def add_record(kind, project, equipment, number, ppm_file="", wcc_file=""):
    conn = db()
    conn.execute(
        """INSERT INTO records(email,kind,project,equipment,number,created_at,ppm_file,wcc_file)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            st.session_state.user, kind, project, equipment, number,
            datetime.now().isoformat(timespec="seconds"), ppm_file, wcc_file
        )
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

# ---------- Sidebar ----------
with st.sidebar:
    logo = ASSETS / "EIFM_logo.jpg"
    if logo.exists():
        st.image(str(logo), width=95)
    st.markdown("### EIFM WCC & PPM")
    st.caption(st.session_state.user)
    page = st.radio(
        "Menu",
        ["Dashboard", "New PPM", "New WCC", "My Records"],
        index=0,
    )
    if st.button("Sign out", use_container_width=True):
        st.session_state.user = None
        st.rerun()

# ---------- Dashboard ----------
if page == "Dashboard":
    st.title("📋 EIFM WCC & PPM")
    st.markdown(
        '<div class="eifm-card"><h3>Original templates are used</h3>'
        '<div class="small-muted">PPM uses the supplied Excel worksheets. WCC uses the supplied EIFMEN08 Word template.</div></div>',
        unsafe_allow_html=True,
    )
    records = get_records()
    a,b,c = st.columns(3)
    a.metric("My Records", len(records))
    b.metric("Equipment Templates", len(EQUIPMENT_SHEETS))
    c.metric("PPM Excel Templates", 2)
    st.subheader("Equipment available from supplied Excel files")
    st.write(", ".join(EQUIPMENT_SHEETS))

# ---------- New PPM ----------
elif page == "New PPM":
    st.title("🛠️ New PPM Task Sheet")
    st.caption("The selected equipment sheet is copied from the supplied Excel workbook; its layout/format is not rebuilt from scratch.")

    with st.form("ppm_form"):
        c1,c2 = st.columns(2)
        with c1:
            project = st.text_input("Project Name")
            location = st.text_input("Location")
            unit = st.text_input("Unit Number")
            frequency = st.selectbox("Frequency", ["Monthly", "Quarterly", "Semi-Annual", "Annual", "Corrective / Complaint"])
            category = st.text_input("Category")
            equipment = st.selectbox("Equipment Type", EQUIPMENT_SHEETS)
        with c2:
            fiscal_year = st.number_input("Fiscal Year", min_value=2000, max_value=2100, value=date.today().year)
            wo = st.text_input("WO Number")
            month = st.selectbox("Scheduled Month", [
                "January","February","March","April","May","June",
                "July","August","September","October","November","December"
            ], index=date.today().month-1)
            service_date = st.date_input("Date of Service", value=date.today())
            start = st.time_input("Time Start", value=time(8,0))
            finish = st.time_input("Time Finish", value=time(17,0))

        st.subheader("Checklist")
        # Load the exact task text from the selected supplied worksheet.
        from generate_sheet import read_template_tasks
        template_tasks = read_template_tasks(equipment)
        if template_tasks:
            st.info("Tasks below are loaded from the selected original Excel worksheet. You may edit them before generating.")
        tasks_text = st.text_area("Service Specification Tasks (one per line)", "\n".join(template_tasks), height=260)
        tasks = split_tasks(tasks_text)

        statuses = {}
        remarks = {}
        followups = {}
        if tasks:
            st.markdown("#### Mark each task")
            for i, task in enumerate(tasks, start=1):
                x1,x2,x3,x4 = st.columns([5,1,1,2])
                with x1:
                    st.write(f"**{i}.** {task}")
                with x2:
                    statuses[i] = st.checkbox("OK", key=f"ppm_ok_{i}")
                with x3:
                    statuses[f"no_{i}"] = st.checkbox("Not OK", key=f"ppm_no_{i}")
                with x4:
                    remarks[i] = st.text_input("Remarks", key=f"ppm_rem_{i}", label_visibility="collapsed")
                followups[i] = st.text_input("Follow-up WO", key=f"ppm_fu_{i}", label_visibility="collapsed")

        technician = st.text_input("Technician Date/Sign")
        engineer = st.text_input("Eng./Sup Date Sign")
        summary = st.text_area("Report Summary of Maintenance", height=100)
        generate = st.form_submit_button("Generate PPM Excel", type="primary", use_container_width=True)

    if generate:
        if not project.strip():
            st.error("Project Name is required.")
        else:
            out = OUTPUTS / f"PPM_{equipment}_{wo or 'WO'}.xlsx"
            create_ppm_from_template(
                equipment=equipment,
                project=project,
                location=location,
                unit=unit,
                frequency=frequency,
                category=category,
                fiscal_year=fiscal_year,
                wo_number=wo,
                scheduled_month=month,
                service_date=service_date.strftime("%d/%m/%Y"),
                time_start=start.strftime("%H:%M"),
                time_finish=finish.strftime("%H:%M"),
                tasks=tasks,
                statuses=statuses,
                remarks=remarks,
                followups=followups,
                technician=technician,
                engineer=engineer,
                summary=summary,
                output_path=out,
            )
            add_record("PPM", project, equipment, wo, str(out.name), "")
            st.success("PPM Excel generated using the supplied worksheet template.")
            st.download_button(
                "📥 Download PPM Excel",
                data=out.read_bytes(),
                file_name=out.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

# ---------- New WCC ----------
elif page == "New WCC":
    st.title("📄 New Work Completion Certificate")
    st.caption("The supplied EIFMEN08 Version R3 Word document is used as the base template.")

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
        with c2:
            site_sig = st.text_input("Signature of Site in Charge")
            site_name = st.text_input("Site in Charge Name")
            site_date = st.text_input("Site in Charge Date")
            site_id = st.text_input("Site in Charge ID")
            hod_sig = st.text_input("Signature of HOD")
            hod_name = st.text_input("HOD Name")
            hod_date = st.text_input("HOD Date")
            hod_id = st.text_input("HOD ID")

        st.subheader("Enclosed documents")
        docs = st.multiselect(
            "Select enclosed documents",
            ["LPO", "Invoice", "Delivery Note", "Petty Cash", "Material Requisition", "Job Completion"],
            default=["Job Completion"],
        )
        c1,c2,c3 = st.columns(3)
        with c1:
            client_sig = st.text_input("Client Signature")
            client_name = st.text_input("Client Name")
        with c2:
            client_phone = st.text_input("Client Phone No.")
            satisfaction = st.selectbox("Satisfaction", ["1. Poor","2. Satisfied","3. Good","4. Very Good","5. Excellent"])
        with c3:
            remarks = st.text_area("Remarks / Suggestions", height=100)
            client_sign_date = st.text_input("Client Signature Date")

        generate = st.form_submit_button("Generate WCC", type="primary", use_container_width=True)

    if generate:
        if not job.strip() or not client.strip() or not project.strip():
            st.error("Job Order Number, Client and Project are required.")
        else:
            out = OUTPUTS / f"WCC_{job.replace('/', '-')}.docx"
            create_wcc_from_template(
                job_order=job, client=client, project=project, location=location, tel=tel,
                details=details, completion=completion,
                site_sig=site_sig, site_name=site_name, site_date=site_date, site_id=site_id,
                hod_sig=hod_sig, hod_name=hod_name, hod_date=hod_date, hod_id=hod_id,
                docs=docs, client_sig=client_sig, client_name=client_name,
                client_phone=client_phone, satisfaction=satisfaction,
                remarks=remarks, client_sign_date=client_sign_date,
                output_path=out,
            )
            add_record("WCC", project, "", job, "", str(out.name))
            st.success("WCC generated from the supplied EIFMEN08 template.")
            st.download_button(
                "📥 Download WCC Word",
                data=out.read_bytes(),
                file_name=out.name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

# ---------- My Records ----------
elif page == "My Records":
    st.title("📚 My Records")
    rows = get_records()
    if not rows:
        st.info("No records yet.")
    else:
        for rid,kind,project,equipment,number,created,ppm_file,wcc_file in rows:
            with st.expander(f"{kind} | {project} | {number} | {created}"):
                st.write("Equipment:", equipment or "-")
                if ppm_file:
                    p = OUTPUTS / ppm_file
                    if p.exists():
                        st.download_button("Download PPM", p.read_bytes(), p.name,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"ppm_{rid}")
                if wcc_file:
                    p = OUTPUTS / wcc_file
                    if p.exists():
                        st.download_button("Download WCC", p.read_bytes(), p.name,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"wcc_{rid}")
