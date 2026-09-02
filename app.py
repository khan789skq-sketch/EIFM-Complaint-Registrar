from pathlib import Path
from datetime import date, time, datetime
import hashlib, secrets, sqlite3, json, shutil, zipfile, mimetypes

import openpyxl
import streamlit as st

from generate_sheet import (
    EQUIPMENT_SHEETS, create_ppm_from_template, create_wcc_from_template,
    read_template_tasks, copy_checklist_workbook, EXCEL_1, EXCEL_3, WCC_TEMPLATE,
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUTS = BASE_DIR / 'outputs'; OUTPUTS.mkdir(exist_ok=True)
DATA = BASE_DIR / 'data'; DATA.mkdir(exist_ok=True)
CHECKLISTS = DATA / 'building_checklists'; CHECKLISTS.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / 'eifm_app.db'
LOGO = BASE_DIR / 'EIFM_logo.jpg'

st.set_page_config(page_title='EIFM WCC & PPM', page_icon='📋', layout='wide')
st.markdown('''<style>
.stApp{background:linear-gradient(135deg,#07151a 0%,#101c22 55%,#07151a 100%)}
[data-testid="stSidebar"]{background:#0b151a}.block-container{padding-top:1.2rem;padding-bottom:2rem}
.eifm-card{padding:18px;border-radius:14px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.035);margin-bottom:14px}
.small-muted{color:#9aa9af;font-size:.88rem}
</style>''', unsafe_allow_html=True)


def db():
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY,password_hash TEXT NOT NULL,created_at TEXT NOT NULL)')
    conn.execute('''CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL,kind TEXT NOT NULL,project TEXT,
        equipment TEXT,number TEXT,created_at TEXT NOT NULL,file_path TEXT,checklist_path TEXT)''')
    # Upgrade older DBs safely.
    cols={r[1] for r in conn.execute('PRAGMA table_info(records)').fetchall()}
    if 'checklist_path' not in cols: conn.execute('ALTER TABLE records ADD COLUMN checklist_path TEXT')
    conn.commit(); return conn


def hash_password(password):
    salt=secrets.token_bytes(16); digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,200000)
    return salt.hex()+'$'+digest.hex()

def verify_password(password,stored):
    try:
        salt,digest=stored.split('$',1); got=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200000)
        return secrets.compare_digest(got.hex(),digest)
    except Exception:return False

def authenticate(email,password):
    with db() as c:r=c.execute('SELECT password_hash FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
    return bool(r and verify_password(password,r['password_hash']))

def create_user(email,password):
    email=email.strip().lower()
    if not email or '@' not in email:return False,'Enter a valid email.'
    if len(password)<6:return False,'Password must be at least 6 characters.'
    try:
        with db() as c:c.execute('INSERT INTO users VALUES(?,?,?)',(email,hash_password(password),datetime.now().isoformat(timespec='seconds')))
        return True,'Account created.'
    except sqlite3.IntegrityError:return False,'This email is already registered.'

def add_record(kind,project,equipment,number,file_path,checklist_path=''):
    with db() as c:c.execute('''INSERT INTO records(email,kind,project,equipment,number,created_at,file_path,checklist_path) VALUES(?,?,?,?,?,?,?,?)''',
        (st.session_state.user,kind,project,equipment,number,datetime.now().isoformat(timespec='seconds'),str(file_path),str(checklist_path or '')))

def get_records():
    with db() as c:return c.execute('SELECT * FROM records WHERE email=? ORDER BY id DESC',(st.session_state.user,)).fetchall()

def safe_name(text):
    text=str(text or '').strip(); return ''.join(ch if ch.isalnum() or ch in '-_ .' else '_' for ch in text).replace(' ','_') or 'Document'

def read_tasks_for_workbook(path,equipment):
    if not path:return []
    try:
        wb=openpyxl.load_workbook(path,read_only=True,data_only=False)
        if equipment not in wb.sheetnames:return []
        ws=wb[equipment]; tasks=[]; header=None
        for r in range(1,ws.max_row+1):
            if str(ws.cell(r,1).value or '').strip().lower()=='sl. no.': header=r; break
        if header:
            for r in range(header+1,ws.max_row+1):
                a,b=ws.cell(r,1).value,ws.cell(r,2).value
                if isinstance(a,(int,float)) and b:tasks.append(str(b))
                elif str(a or '').strip().upper().startswith('GENERAL NOTICE'):break
        wb.close(); return tasks
    except Exception:return []

def checklist_library():
    st.subheader('🏢 Building Checklist Library')
    st.write('Upload and save one or more Excel checklist files for each building. A building can use a different workbook, with any number of checklist pages/sheets.')
    files=list(CHECKLISTS.glob('*'))
    if files:
        st.write('Saved checklists:')
        for p in sorted(files): st.write('•',p.name)
    with st.form('checklist_library_form'):
        building=st.text_input('Building / Project Name')
        upload=st.file_uploader('Attach Excel Checklist (.xlsx)',type=['xlsx'])
        save=st.form_submit_button('Save Building Checklist',type='primary')
    if save:
        if not building.strip() or not upload:st.error('Building name and Excel checklist are required.')
        else:
            out=CHECKLISTS/(safe_name(building)+'.xlsx'); out.write_bytes(upload.getvalue())
            st.success(f'Saved checklist for {building}.')

def available_checklists():
    return sorted(CHECKLISTS.glob('*.xlsx'))

def checklist_options():
    opts={'Use original All-3.xlsx':EXCEL_3,'Use original All.xlsx':EXCEL_1}
    for p in available_checklists():opts[f'Building checklist: {p.stem}']=p
    return opts

def checklist_editor(equipment):
    tasks=read_template_tasks(equipment)
    if not tasks: st.warning('No checklist rows were found in this equipment sheet.'); return [],{},{},{}
    st.info('The selected equipment sheet is loaded directly from the original Excel template.')
    text=st.text_area('Service Specification Tasks (one per line)','\n'.join(tasks),height=220)
    tasks=[x.strip() for x in text.splitlines() if x.strip()]
    statuses,remarks,followups={},{},{}
    for i,task in enumerate(tasks,1):
        c1,c2,c3,c4=st.columns([5,1,1,3]); c1.write(f'{i}. {task}')
        statuses[i]=c2.checkbox('OK',key=f'ok_{equipment}_{i}')
        statuses[f'no_{i}']=c3.checkbox('Not OK',key=f'no_{equipment}_{i}')
        remarks[i]=c4.text_input('Remarks',key=f'rem_{equipment}_{i}',label_visibility='collapsed')
        followups[i]=c4.text_input('Follow-up WO',key=f'fol_{equipment}_{i}',label_visibility='collapsed')
    return tasks,statuses,remarks,followups

if 'user' not in st.session_state:st.session_state.user=None
if not st.session_state.user:
    st.title('EIFM WCC & PPM')
    if LOGO.exists():st.image(str(LOGO),width=140)
    st.caption('EIFM PPM & WCC Generator')
    a,b=st.tabs(['Sign in','Sign up'])
    with a:
        e=st.text_input('Email',key='login_email'); p=st.text_input('Password',type='password',key='login_password')
        if st.button('Sign in',type='primary',use_container_width=True):
            if authenticate(e,p):st.session_state.user=e.strip().lower();st.rerun()
            else:st.error('Email or password is incorrect.')
    with b:
        e=st.text_input('Email',key='signup_email');p1=st.text_input('Password',type='password',key='signup_p1');p2=st.text_input('Confirm password',type='password',key='signup_p2')
        if st.button('Create account',use_container_width=True):
            if p1!=p2:st.error('Passwords do not match.')
            else:
                ok,msg=create_user(e,p1);(st.success if ok else st.error)(msg)
    st.stop()

with st.sidebar:
    if LOGO.exists():st.image(str(LOGO),width=95)
    st.markdown('### EIFM WCC & PPM');st.caption(st.session_state.user)
    page=st.radio('Menu',['Dashboard','Checklist Library','New PPM','New WCC','My Records'])
    if st.button('Sign out',use_container_width=True):st.session_state.user=None;st.rerun()

if page=='Dashboard':
    rows=get_records();st.title('📋 EIFM WCC & PPM Generator')
    st.markdown('<div class="eifm-card"><h3>Original templates are preserved</h3><div class="small-muted">PPM uses the supplied equipment worksheets. WCC uses the supplied EIFMEN08 front page. Building checklists can be different for every building.</div></div>',unsafe_allow_html=True)
    a,b,c=st.columns(3);a.metric('My Records',len(rows));b.metric('Equipment Templates',len(EQUIPMENT_SHEETS));c.metric('Saved Building Checklists',len(available_checklists()))
    st.subheader('PPM');st.write('Planned Preventive Maintenance Service Complete as per Attached Check List')
    st.write('PPM Number: 1st PPM / 2nd PPM / 3rd PPM / 4th PPM')
    st.subheader('Equipment worksheets');st.write(', '.join(EQUIPMENT_SHEETS) if EQUIPMENT_SHEETS else 'No Excel templates found.')

elif page=='Checklist Library':checklist_library()

elif page=='New PPM':
    st.title('🛠️ New PPM Task Sheet')
    if not EQUIPMENT_SHEETS:st.error('All.xlsx / All-3.xlsx could not be found.');st.stop()
    with st.form('ppm_form'):
        c1,c2=st.columns(2)
        with c1:
            project=st.text_input('Building / Project Name');location=st.text_input('Location');unit=st.text_input('Unit Number')
            frequency=st.selectbox('Frequency',['Monthly','Quarterly','Semi-Annual','Annual','Corrective / Complaint']);category=st.text_input('Category');equipment=st.selectbox('Equipment',EQUIPMENT_SHEETS)
        with c2:
            fiscal_year=st.number_input('Fiscal Year',2000,2100,date.today().year);wo=st.text_input('WO Number');ppm_number=st.selectbox('PPM Number',['1st PPM','2nd PPM','3rd PPM','4th PPM'])
            month=st.selectbox('Scheduled Month',['January','February','March','April','May','June','July','August','September','October','November','December'],index=date.today().month-1);service_date=st.date_input('Date of Service',date.today());start=st.time_input('Time Start',time(8));finish=st.time_input('Time Finish',time(17))
        opts=checklist_options();clabel=st.selectbox('Building Checklist',list(opts.keys()),key='ppm_checklist');st.caption('This checklist is attached separately with the generated PPM/WCC package; it may contain any number of sheets/pages.')
        st.markdown('**Details Of Work**');st.info('Planned Preventive Maintenance Service Complete as per Attached Check List')
        tasks,statuses,remarks,followups=checklist_editor(equipment);technician=st.text_input('Tech. Date/Sign');engineer=st.text_input('Eng./Sup Date Sign');summary=st.text_area('REPORT SUMMARY',height=100)
        generate=st.form_submit_button('Generate PPM Excel + Checklist',type='primary',use_container_width=True)
    if generate:
        if not project.strip():st.error('Building / Project Name is required.')
        else:
            stamp=f'{datetime.now():%Y%m%d_%H%M%S}';out=OUTPUTS/f'PPM_{safe_name(equipment)}_{safe_name(ppm_number)}_{stamp}.xlsx';cl=OUTPUTS/f'Checklist_{safe_name(project)}_{stamp}.xlsx'
            try:
                create_ppm_from_template(equipment,project,location,unit,frequency,category,fiscal_year,wo,ppm_number,month,service_date.strftime('%d/%m/%Y'),start.strftime('%H:%M'),finish.strftime('%H:%M'),tasks,statuses,remarks,followups,technician,engineer,summary,out)
                copy_checklist_workbook(opts[clabel],equipment if clabel.startswith('Use original') else None,cl)
                add_record('PPM',project,equipment,ppm_number,out,cl);st.success('PPM generated successfully.');st.download_button('📥 Download PPM Excel',out.read_bytes(),out.name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');st.download_button('📎 Download Attached Checklist',cl.read_bytes(),cl.name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            except Exception as exc:st.exception(exc)

elif page=='New WCC':
    st.title('📄 New Work Completion Certificate')
    mode=st.radio('WCC Type',['Normal WCC','PPM WCC'],horizontal=True)
    st.info('Normal WCC = no PPM wording, with Before + After Pictures. PPM WCC = PPM front page + building-specific Excel checklist with any number of sheets/pages.')
    with st.form('wcc_form'):
        c1,c2=st.columns(2)
        with c1:
            job=st.text_input('Job Order Number');client=st.text_input('Client');project=st.text_input('Building / Project');location=st.text_input('Location');tel=st.text_input('Tel. No.')
            equipment=st.selectbox('Equipment (optional)',EQUIPMENT_SHEETS);details=st.text_area('Details of Work',height=150)
            completion=st.text_input('Date & Time of Completion');site_sig=st.text_input('Signature of Site in Charge');site_name=st.text_input('Site in Charge Name');site_date=st.text_input('Site in Charge Date');site_id=st.text_input('Site in Charge ID')
        with c2:
            hod_sig=st.text_input('Signature of HOD');hod_name=st.text_input('HOD Name');hod_date=st.text_input('HOD Date');hod_id=st.text_input('HOD ID');client_sig=st.text_input('Client Signature');client_name=st.text_input('Client Name');client_phone=st.text_input('Client Phone No.');satisfaction=st.selectbox('Satisfaction',['1. Poor','2. Satisfied','3. Good','4. Very Good','5. Excellent']);client_sign_date=st.text_input('Client Signature Date');remarks_wcc=st.text_area('Remarks / Suggestions',height=80)
            ppm_number=st.selectbox('PPM Number',['1st PPM','2nd PPM','3rd PPM','4th PPM']) if mode=='PPM WCC' else None
            ppm_year=st.number_input('PPM Service Year',2000,2100,date.today().year) if mode=='PPM WCC' else None
        docs=st.multiselect('Select enclosed documents',['LPO','Invoice','Delivery Note','Petty Cash','Material Requisition','Job Completion'],default=['Job Completion'])
        if mode=='PPM WCC':
            opts=checklist_options();clabel=st.selectbox('Building Checklist',list(opts.keys()),key='wcc_ppm_checklist')
        else: clabel=None;opts={}
        if mode=='Normal WCC':
            before=st.file_uploader('Before Picture',type=['jpg','jpeg','png'],key='before_pic');after=st.file_uploader('After Picture',type=['jpg','jpeg','png'],key='after_pic')
        else: before=after=None
        generate=st.form_submit_button('Generate WCC Package',type='primary',use_container_width=True)
    if generate:
        if not client.strip() or not project.strip():st.error('Client and Building / Project are required.')
        elif mode=='Normal WCC' and (not before or not after):st.error('Normal WCC requires both Before Picture and After Picture.')
        else:
            stamp=f'{datetime.now():%Y%m%d_%H%M%S}';out=OUTPUTS/f'WCC_{safe_name(project)}_{stamp}.docx';cl=OUTPUTS/f'Checklist_{safe_name(project)}_{stamp}.xlsx' if mode=='PPM WCC' else ''
            try:
                bi=ai=None
                if before:bi=OUTPUTS/f'_before_{stamp}.jpg';bi.write_bytes(before.getvalue())
                if after:ai=OUTPUTS/f'_after_{stamp}.jpg';ai.write_bytes(after.getvalue())
                # Equipment details are shown in the form and automatically inserted when the user leaves Details blank.
                if equipment and not details.strip():
                    details='\n'.join(read_template_tasks(equipment))
                create_wcc_from_template(job,client,project,location,tel,details,completion,site_sig,site_name,site_date,site_id,hod_sig,hod_name,hod_date,hod_id,docs,client_sig,client_name,client_phone,satisfaction,remarks_wcc,client_sign_date,out,bi,ai,ppm_number,ppm_year)
                if mode=='PPM WCC':copy_checklist_workbook(opts[clabel],None,cl)
                add_record(mode,project,equipment,job if mode=='Normal WCC' else ppm_number,out,cl);st.success(f'{mode} generated successfully.')
                st.download_button('📥 Download WCC Word',out.read_bytes(),out.name,'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                if mode=='PPM WCC':st.download_button('📎 Download PPM Excel Checklist',cl.read_bytes(),cl.name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            except Exception as exc:st.exception(exc)

else:
    st.title('📚 My Records');rows=get_records()
    if not rows:st.info('No records yet.')
    for row in rows:
        p=Path(row['file_path']);cp=Path(row['checklist_path']) if row['checklist_path'] else None
        with st.expander(f"{row['kind']} | {row['project'] or '-'} | {row['number'] or '-'} | {row['created_at']}"):
            st.write('Equipment:',row['equipment'] or '-')
            if p.exists():
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if p.suffix.lower()=='.xlsx' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';st.download_button('📥 Download Main File',p.read_bytes(),p.name,mime,key=f'download_{row["id"]}')
            if cp and cp.exists():st.download_button('📎 Download Checklist',cp.read_bytes(),cp.name,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=f'check_{row["id"]}')
