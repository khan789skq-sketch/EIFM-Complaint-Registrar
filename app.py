import streamlit as st
from pathlib import Path
from datetime import date, time, datetime
import sqlite3, hashlib, secrets
import openpyxl
from generate_sheet import EQUIPMENT_SHEETS, generate_ppm, generate_wcc

BASE=Path(__file__).parent
TEMPLATES=BASE/"templates"; OUTPUTS=BASE/"outputs"; DATA=BASE/"data"
OUTPUTS.mkdir(exist_ok=True); DATA.mkdir(exist_ok=True)
DB=DATA/"eifm_app.db"
st.set_page_config(page_title="EIFM PPM & WCC",layout="wide")

def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
    with db() as c:
        c.execute("CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY,password_hash TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT,kind TEXT,project TEXT,equipment TEXT,number TEXT,created_at TEXT,file_path TEXT)")
init()
def hp(p):
    s=secrets.token_bytes(16); d=hashlib.pbkdf2_hmac("sha256",p.encode(),s,200000)
    return s.hex()+"$"+d.hex()
def vp(p,x):
    try:
        s,d=x.split("$",1)
        return secrets.compare_digest(hashlib.pbkdf2_hmac("sha256",p.encode(),bytes.fromhex(s),200000).hex(),d)
    except: return False
def auth(e,p):
    with db() as c: r=c.execute("SELECT password_hash FROM users WHERE email=?",(e.lower().strip(),)).fetchone()
    return bool(r and vp(p,r["password_hash"]))
def adduser(e,p):
    try:
        with db() as c: c.execute("INSERT INTO users VALUES(?,?)",(e.lower().strip(),hp(p)))
        return True
    except: return False
def record(*v):
    with db() as c: c.execute("INSERT INTO records(email,kind,project,equipment,number,created_at,file_path) VALUES(?,?,?,?,?,?,?)",v)

if "user" not in st.session_state: st.session_state.user=None
if not st.session_state.user:
    st.title("EIFM PPM & WCC")
    a,b=st.tabs(["Sign in","Sign up"])
    with a:
        e=st.text_input("Email"); p=st.text_input("Password",type="password")
        if st.button("Sign in",type="primary"):
            if auth(e,p): st.session_state.user=e.lower().strip(); st.rerun()
            else: st.error("Invalid email or password.")
    with b:
        e=st.text_input("Email",key="su_e"); p=st.text_input("Password",type="password",key="su_p"); q=st.text_input("Confirm password",type="password")
        if st.button("Create account"):
            if p!=q: st.error("Passwords do not match.")
            elif len(p)<6: st.error("Password must be at least 6 characters.")
            elif adduser(e,p): st.success("Account created.")
            else: st.error("Email already registered.")
    st.stop()

with st.sidebar:
    st.title("EIFM")
    menu=st.radio("Menu",["Dashboard","New PPM","New WCC","My Records"])
    if st.button("Sign out"): st.session_state.user=None; st.rerun()

if menu=="Dashboard":
    st.title("EIFM PPM & WCC Generator")
    st.info("PPM uses the supplied Excel equipment sheets. The original equipment workbook is preserved; the selected sheet is not rebuilt.")
    st.write("PPM numbering: 1st PPM, 2nd PPM, 3rd PPM, 4th PPM.")
    st.write("Details of Work: Planned Preventive Maintenance Service Complete as per Attached Check List")

elif menu=="New PPM":
    st.title("New PPM")
    with st.form("ppm"):
        c1,c2=st.columns(2)
        with c1:
            project=st.text_input("Project Name"); location=st.text_input("Location"); unit=st.text_input("Unit Number")
            frequency=st.selectbox("Frequency",["Monthly","Quarterly","Semi-Annual","Annual","Corrective / Complaint"])
            category=st.text_input("Category"); equipment=st.selectbox("Equipment",EQUIPMENT_SHEETS)
        with c2:
            fy=st.number_input("Fiscal Year",2000,2100,date.today().year)
            wo=st.text_input("WO Number")
            ppm=st.selectbox("PPM Number",["1st PPM","2nd PPM","3rd PPM","4th PPM"])
            month=st.selectbox("Scheduled Month",["January","February","March","April","May","June","July","August","September","October","November","December"])
            sd=st.date_input("Date of Service",date.today()); ts=st.time_input("Time Start",time(8,0)); tf=st.time_input("Time Finish",time(17,0))
        st.text_area("Details of Work","Planned Preventive Maintenance Service Complete as per Attached Check List",disabled=True)
        go=st.form_submit_button("Generate PPM",type="primary")
    if go:
        source=next((TEMPLATES/n for n in ["All.xlsx","All-3.xlsx"] if equipment in openpyxl.load_workbook(TEMPLATES/n,read_only=True).sheetnames),None)
        out=OUTPUTS/f"PPM_{ppm.replace(' ','_')}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        generate_ppm(source,equipment,dict(project=project,location=location,unit=unit,frequency=frequency,category=category,equipment=equipment,fiscal_year=fy,wo=wo,ppm=ppm,month=month,service_date=sd,time_start=ts,time_finish=tf),out)
        with db() as c: c.execute("INSERT INTO records(email,kind,project,equipment,number,created_at,file_path) VALUES(?,?,?,?,?,?,?)",(st.session_state.user,"PPM",project,equipment,ppm,datetime.now().isoformat(),str(out)))
        st.success("PPM generated."); st.download_button("Download PPM",out.read_bytes(),out.name)

elif menu=="New WCC":
    st.title("New WCC")
    with st.form("wcc"):
        job=st.text_input("Job Order Number"); client=st.text_input("Client"); project=st.text_input("Project"); location=st.text_input("Location"); tel=st.text_input("Tel. No.")
        details=st.text_area("Details of Work"); site=st.text_input("Site in Charge Name"); siteid=st.text_input("Site in Charge ID"); hod=st.text_input("HOD Name"); hodid=st.text_input("HOD ID")
        cname=st.text_input("Client Name"); phone=st.text_input("Client Phone No."); remarks=st.text_area("Remarks / Suggestions")
        go=st.form_submit_button("Generate WCC",type="primary")
    if go:
        out=OUTPUTS/f"WCC_{datetime.now():%Y%m%d_%H%M%S}.pdf"
        generate_wcc(dict(job=job,client=client,project=project,location=location,tel=tel,details=details,site=site,siteid=siteid,hod=hod,hodid=hodid,cname=cname,phone=phone,remarks=remarks),out)
        with db() as c: c.execute("INSERT INTO records(email,kind,project,equipment,number,created_at,file_path) VALUES(?,?,?,?,?,?,?)",(st.session_state.user,"WCC",project,"",job,datetime.now().isoformat(),str(out)))
        st.success("WCC generated."); st.download_button("Download WCC",out.read_bytes(),out.name,"application/pdf")

else:
    st.title("My Records")
    with db() as c: rows=c.execute("SELECT * FROM records WHERE email=? ORDER BY id DESC",(st.session_state.user,)).fetchall()
    for r in rows:
        p=Path(r["file_path"]); st.write(f"**{r['kind']}** — {r['project'] or '-'} — {r['number'] or '-'}")
        if p.exists(): st.download_button("Download",p.read_bytes(),p.name,key=str(r["id"]))
