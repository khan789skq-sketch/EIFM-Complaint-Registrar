from pathlib import Path
from datetime import date, time, datetime
import hashlib, secrets, sqlite3, shutil, zipfile

import openpyxl
from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas

from generate_sheet import (
    EQUIPMENT_SHEETS, create_ppm_package, create_wcc_from_template,
    read_template_tasks, copy_selected_equipment_workbook, EXCEL_1, EXCEL_3,
)

BASE_DIR=Path(__file__).resolve().parent
OUTPUTS=BASE_DIR/'outputs'; OUTPUTS.mkdir(exist_ok=True)
DATA=BASE_DIR/'data'; DATA.mkdir(exist_ok=True)
CHECKLISTS=DATA/'building_checklists'; CHECKLISTS.mkdir(exist_ok=True)
DB_PATH=BASE_DIR/'eifm_app.db'; LOGO=BASE_DIR/'EIFM_logo.jpg'

st.set_page_config(page_title='EIFM WCC & PPM',page_icon='📋',layout='wide')
st.markdown('''<style>
.stApp{background:linear-gradient(135deg,#07151a 0%,#101c22 55%,#07151a 100%)}
[data-testid="stSidebar"]{background:#0b151a}.block-container{padding-top:1.2rem;padding-bottom:2rem}
.eifm-card{padding:18px;border-radius:14px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.035);margin-bottom:14px}
.small-muted{color:#9aa9af;font-size:.88rem}
</style>''',unsafe_allow_html=True)

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY,password_hash TEXT NOT NULL,created_at TEXT NOT NULL)')
    c.execute('''CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL,kind TEXT NOT NULL,project TEXT,equipment TEXT,number TEXT,created_at TEXT NOT NULL,file_path TEXT,checklist_path TEXT,package_path TEXT)''')
    cols={r[1] for r in c.execute('PRAGMA table_info(records)').fetchall()}
    for col in ['checklist_path','package_path']:
        if col not in cols: c.execute(f'ALTER TABLE records ADD COLUMN {col} TEXT')
    c.commit(); return c

def hash_password(password):
    salt=secrets.token_bytes(16); d=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,200000); return salt.hex()+'$'+d.hex()
def verify_password(password,stored):
    try:
        salt,d=stored.split('$',1); got=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),200000); return secrets.compare_digest(got.hex(),d)
    except Exception:return False
def authenticate(e,p):
    with db() as c:r=c.execute('SELECT password_hash FROM users WHERE email=?',(e.strip().lower(),)).fetchone()
    return bool(r and verify_password(p,r['password_hash']))
def create_user(e,p):
    e=e.strip().lower()
    if not e or '@' not in e:return False,'Enter a valid email.'
    if len(p)<6:return False,'Password must be at least 6 characters.'
    try:
        with db() as c:c.execute('INSERT INTO users VALUES(?,?,?)',(e,hash_password(p),datetime.now().isoformat(timespec='seconds')))
        return True,'Account created.'
    except sqlite3.IntegrityError:return False,'This email is already registered.'
def add_record(kind,project,equipment,number,file_path,checklist_path='',package_path=''):
    with db() as c:c.execute('INSERT INTO records(email,kind,project,equipment,number,created_at,file_path,checklist_path,package_path) VALUES(?,?,?,?,?,?,?,?,?)',(st.session_state.user,kind,project,equipment,number,datetime.now().isoformat(timespec='seconds'),str(file_path),str(checklist_path or ''),str(package_path or '')))
def get_records():
    with db() as c:return c.execute('SELECT * FROM records WHERE email=? ORDER BY id DESC',(st.session_state.user,)).fetchall()
def safe_name(s):
    s=str(s or '').strip(); return ''.join(ch if ch.isalnum() or ch in '-_ .' else '_' for ch in s).replace(' ','_') or 'Document'

def available_checklists():return sorted(CHECKLISTS.glob('*.xlsx'))
def checklist_options():
    o={'Use original All-3.xlsx':EXCEL_3,'Use original All.xlsx':EXCEL_1}
    for p in available_checklists():o[f'Building checklist: {p.stem}']=p
    return o

def building_checklist_library():
    st.subheader('🏢 Building Checklist Library')
    st.write('Save one Excel checklist per building. Each saved workbook can contain any number of sheets/pages.')
    for p in available_checklists():st.write('•',p.name)
    building=st.text_input('Building / Project Name')
    up=st.file_uploader('Attach Excel Checklist (.xlsx)',type=['xlsx'],key='library_upload')
    if st.button('Save Building Checklist',type='primary'):
        if not building.strip() or not up: st.error('Building name and Excel checklist are required.')
        else:
            out=CHECKLISTS/(safe_name(building)+'.xlsx'); out.write_bytes(up.getvalue()); st.success(f'Saved checklist for {building}.')

def equipment_editor(selected,key_prefix):
    task_data={}; statuses={}; remarks={}; followups={}
    for equipment in selected:
        with st.expander(f'📋 {equipment} — checklist details',expanded=True):
            tasks=read_template_tasks(equipment); task_data[equipment]=tasks
            if not tasks: st.warning(f'No checklist rows found for {equipment}.'); continue
            st.caption(f'{equipment}: only this selected equipment checklist is shown here.')
            for i,task in enumerate(tasks,1):
                c1,c2,c3,c4=st.columns([5,1,1,3]); c1.write(f'{i}. {task}')
                statuses[(equipment,i)]=c2.checkbox('OK',key=f'{key_prefix}_ok_{equipment}_{i}')
                statuses[(equipment,f'no_{i}')]=c3.checkbox('Not OK',key=f'{key_prefix}_no_{equipment}_{i}')
                remarks[(equipment,i)]=c4.text_input('Remarks',key=f'{key_prefix}_rem_{equipment}_{i}',label_visibility='collapsed')
                followups[(equipment,i)]=c4.text_input('Follow-up WO',key=f'{key_prefix}_fol_{equipment}_{i}',label_visibility='collapsed')
    return task_data,statuses,remarks,followups

def crop_photo(uploaded,prefix):
    if not uploaded:return None
    img=Image.open(uploaded).convert('RGB')
    st.image(img,caption=f'{prefix} original',width=260)
    zoom=st.slider(f'{prefix} crop/zoom',1.0,3.0,1.0,0.1,key=f'{prefix}_zoom')
    x=st.slider(f'{prefix} horizontal',0,100,50,key=f'{prefix}_x')
    y=st.slider(f'{prefix} vertical',0,100,50,key=f'{prefix}_y')
    target_ratio=4/3
    crop_w=img.width/zoom; crop_h=crop_w/target_ratio
    if crop_h>img.height/zoom: crop_h=img.height/zoom; crop_w=crop_h*target_ratio
    max_x=max(0,img.width-crop_w); max_y=max(0,img.height-crop_h)
    left=max_x*x/100; top=max_y*y/100
    cropped=img.crop((int(left),int(top),int(left+crop_w),int(top+crop_h))).resize((900,675),Image.LANCZOS)
    st.image(cropped,caption=f'{prefix} final crop',width=260)
    return cropped

def save_pil(img,path):
    if img is not None: img.save(path,'JPEG',quality=92)

def make_zip(folder,zip_path):
    with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(folder))
    return zip_path

def signature_pad(label,key):
    st.caption(f'{label} — sign with finger/stylus below')
    result=st_canvas(fill_color='rgba(255,255,255,0)',stroke_width=3,stroke_color='#000000',background_color='#ffffff',height=110,width=420,drawing_mode='freedraw',key=key,display_toolbar=True)
    return result

if 'user' not in st.session_state:st.session_state.user=None
if not st.session_state.user:
    st.title('EIFM WCC & PPM')
    if LOGO.exists():st.image(str(LOGO),width=140)
    a,b=st.tabs(['Sign in','Sign up'])
    with a:
        e=st.text_input('Email',key='login_email');p=st.text_input('Password',type='password',key='login_password')
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
    a,b,c=st.columns(3);a.metric('My Records',len(rows));b.metric('Equipment Templates',len(EQUIPMENT_SHEETS));c.metric('Building Checklists',len(available_checklists()))
    st.write('PPM = Planned Preventive Maintenance Service. Original Excel worksheets and EIFMEN08 WCC template are used as the base.')
    st.write('Equipment available:',', '.join(EQUIPMENT_SHEETS))

elif page=='Checklist Library':building_checklist_library()

elif page=='New PPM':
    st.title('🛠️ New PPM')
    project=st.text_input('Building / Project Name'); location=st.text_input('Location'); unit=st.text_input('Unit Number')
    c1,c2=st.columns(2)
    with c1: frequency=st.selectbox('Frequency',['Monthly','Quarterly','Semi-Annual','Annual','Corrective / Complaint']); category=st.text_input('Category'); selected=st.multiselect('Equipment — select ONE or MANY',EQUIPMENT_SHEETS,key='ppm_equipment')
    with c2: fiscal_year=st.number_input('Fiscal Year',2000,2100,date.today().year);wo=st.text_input('WO Number');ppm_number=st.selectbox('PPM Number',['1st PPM','2nd PPM','3rd PPM','4th PPM']);month=st.selectbox('Scheduled Month',['January','February','March','April','May','June','July','August','September','October','November','December'],index=date.today().month-1);service_date=st.date_input('Date of Service',date.today());start=st.time_input('Time Start',time(8));finish=st.time_input('Time Finish',time(17))
    opts=checklist_options(); clabel=st.selectbox('Building Checklist to attach as ONE Excel file',list(opts.keys()),key='ppm_checklist')
    if selected: task_data,statuses,remarks,followups=equipment_editor(selected,'ppm')
    else: task_data,statuses,remarks,followups={}, {}, {}, {}; st.info('Select one or more equipment. Only selected equipment details will appear.')
    technician=st.text_input('Technician Name / Sign');engineer=st.text_input('Engineer / Supervisor Name / Sign');summary=st.text_area('REPORT SUMMARY')
    if st.button('Generate PPM',type='primary',use_container_width=True):
        if not project.strip() or not selected:st.error('Building / Project and at least one equipment are required.')
        else:
            stamp=f'{datetime.now():%Y%m%d_%H%M%S}';folder=OUTPUTS/f'PPM_{safe_name(project)}_{stamp}';folder.mkdir(parents=True,exist_ok=True)
            main=folder/'PPM.xlsx'; checklist=folder/'Checklist.xlsx'; package=OUTPUTS/f'PPM_PACKAGE_{safe_name(project)}_{stamp}.zip'
            try:
                create_ppm_package(selected,project,location,unit,frequency,category,fiscal_year,wo,ppm_number,month,service_date.strftime('%d/%m/%Y'),start.strftime('%H:%M'),finish.strftime('%H:%M'),task_data,statuses,remarks,followups,technician,engineer,summary,main)
                copy_selected_equipment_workbook(selected,checklist)
                make_zip(folder,package);add_record('PPM',project,', '.join(selected),ppm_number,main,checklist,package)
                st.success('PPM generated. One checklist Excel contains all selected equipment sheets.')
                st.download_button('📦 Download PPM Package',package.read_bytes(),package.name,'application/zip')
            except Exception as e:st.exception(e)

elif page=='New WCC':
    st.title('📄 New Work Completion Certificate')
    mode=st.radio('WCC Type',['Normal WCC','PPM WCC'],horizontal=True)
    st.info('Normal WCC = no PPM wording + Before/After pictures on one page. PPM WCC = PPM front page + ONE Excel checklist containing any number of selected equipment sheets.')
    c1,c2=st.columns(2)
    with c1:
        job=st.text_input('Job Order Number');client=st.text_input('Client');project=st.text_input('Building / Project');location=st.text_input('Location');tel=st.text_input('Tel. No.')
        selected=st.multiselect('Equipment — select ONE or MANY',EQUIPMENT_SHEETS,key='wcc_equipment')
        details=st.text_area('Details of Work',height=150,help='If left blank, details from ONLY the selected equipment are inserted.')
        completion=st.text_input('Date & Time of Completion')
    with c2:
        client_name=st.text_input('Client Name');client_phone=st.text_input('Client Phone No.');satisfaction=st.selectbox('Satisfaction',['1. Poor','2. Satisfied','3. Good','4. Very Good','5. Excellent']);client_sign_date=st.text_input('Client Signature Date');remarks_wcc=st.text_area('Remarks / Suggestions',height=80)
        docs=st.multiselect('Enclosed documents',['LPO','Invoice','Delivery Note','Petty Cash','Material Requisition','Job Completion'],default=['Job Completion'])
        ppm_number=st.selectbox('PPM Number',['1st PPM','2nd PPM','3rd PPM','4th PPM']) if mode=='PPM WCC' else None
        ppm_year=st.number_input('PPM Service Year',2000,2100,date.today().year) if mode=='PPM WCC' else None
    if selected:
        task_data,statuses,remarks,followups=equipment_editor(selected,'wcc')
        if not details.strip():
            parts=[]
            for eq in selected:
                parts.append(f'{eq}:')
                parts.extend(read_template_tasks(eq))
            details='\n'.join(parts)
    else: task_data,statuses,remarks,followups={}, {}, {}, {}

    if mode=='PPM WCC':
        opts=checklist_options();clabel=st.selectbox('Building Checklist — ONE Excel file, any number of sheets/pages',list(opts.keys()),key='wcc_checklist')
        before=after=None
    else:
        clabel=None;opts={}
        st.subheader('Before / After Pictures — both stay on the SAME WCC page')
        p1,p2=st.columns(2)
        with p1: before_up=st.file_uploader('Before Picture',type=['jpg','jpeg','png'],key='before_pic')
        with p2: after_up=st.file_uploader('After Picture',type=['jpg','jpeg','png'],key='after_pic')
        p1,p2=st.columns(2)
        with p1: before=crop_photo(before_up,'Before')
        with p2: after=crop_photo(after_up,'After')

    st.subheader('Signatures — actual signature, not typed text')
    s1,s2,s3=st.columns(3)
    with s1: site_canvas=signature_pad('Site in Charge Signature','site_signature_pad');site_name=st.text_input('Site in Charge Name');site_date=st.text_input('Site Date');site_id=st.text_input('Site ID')
    with s2: hod_canvas=signature_pad('HOD Signature','hod_signature_pad');hod_name=st.text_input('HOD Name');hod_date=st.text_input('HOD Date');hod_id=st.text_input('HOD ID')
    with s3: client_canvas=signature_pad('Client Signature','client_signature_pad')

    if st.button('Generate WCC Package',type='primary',use_container_width=True):
        if not client.strip() or not project.strip():st.error('Client and Building / Project are required.')
        elif mode=='Normal WCC' and (before is None or after is None):st.error('Normal WCC requires both Before and After pictures.')
        elif mode=='PPM WCC' and not selected:st.error('Select at least one equipment for the PPM WCC checklist.')
        else:
            stamp=f'{datetime.now():%Y%m%d_%H%M%S}';folder=OUTPUTS/f'WCC_{safe_name(project)}_{stamp}';folder.mkdir(parents=True,exist_ok=True);out=folder/'WCC.docx';cl=folder/'Checklist.xlsx' if mode=='PPM WCC' else None;package=OUTPUTS/f'WCC_PACKAGE_{safe_name(project)}_{stamp}.zip'
            try:
                site_img=folder/'site_signature.png';hod_img=folder/'hod_signature.png';client_img=folder/'client_signature.png'
                for result,path in [(site_canvas,site_img),(hod_canvas,hod_img),(client_canvas,client_img)]:
                    if result is not None and result.image_data is not None and result.image_data.any(): Image.fromarray(result.image_data.astype('uint8')).save(path)
                before_path=folder/'before.jpg';after_path=folder/'after.jpg';save_pil(before,before_path);save_pil(after,after_path)
                create_wcc_from_template(job,client,project,location,tel,details,completion,site_img if site_img.exists() else None,site_name,site_date,site_id,hod_img if hod_img.exists() else None,hod_name,hod_date,hod_id,docs,client_img if client_img.exists() else None,client_name,client_phone,satisfaction,remarks_wcc,client_sign_date,out,before_path if before_path.exists() else None,after_path if after_path.exists() else None,ppm_number,ppm_year)
                if mode=='PPM WCC':copy_selected_equipment_workbook(selected,cl);make_zip(folder,package)
                else: make_zip(folder,package)
                add_record(mode,project,', '.join(selected),job if mode=='Normal WCC' else ppm_number,out,cl or '',package)
                st.success(f'{mode} generated successfully. One page is used for Before/After photos in Normal WCC.')
                st.download_button('📦 Download WCC Package',package.read_bytes(),package.name,'application/zip')
            except Exception as e:st.exception(e)

else:
    st.title('📚 My Records');rows=get_records()
    if not rows:st.info('No records yet.')
    for row in rows:
        with st.expander(f"{row['kind']} | {row['project'] or '-'} | {row['number'] or '-'} | {row['created_at']}"):
            st.write('Equipment:',row['equipment'] or '-')
            for field,label,mime in [('package_path','📦 Download Package','application/zip'),('file_path','📄 Main File',None),('checklist_path','📎 Checklist', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')]:
                p=Path(row[field]) if row[field] else None
                if p and p.exists(): st.download_button(label,p.read_bytes(),p.name,mime or ('application/vnd.openxmlformats-officedocument.wordprocessingml.document' if p.suffix=='.docx' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),key=f'{field}_{row["id"]}')
