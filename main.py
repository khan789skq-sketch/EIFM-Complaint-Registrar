import hashlib, json, secrets, sqlite3, zipfile
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from generate_sheet import (EQUIPMENT_SHEETS, create_wcc_from_template, create_ppm_package,
                            read_template_tasks, copy_selected_equipment_workbook)

BASE = Path(__file__).resolve().parent
DATA = Path('/data') if Path('/data').exists() else BASE / 'data'  # /data = permanent disk on server
OUT = DATA / 'outputs'; OUT.mkdir(parents=True, exist_ok=True)
CL = DATA / 'building_checklists'; CL.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA / 'eifm_app.db'
app = FastAPI()


def db():
    c = sqlite3.connect(DB_PATH); c.row_factory = sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY,password_hash TEXT NOT NULL,created_at TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS tokens(token TEXT PRIMARY KEY,email TEXT NOT NULL,created_at TEXT NOT NULL)')
    c.execute('''CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL,kind TEXT NOT NULL,project TEXT,equipment TEXT,number TEXT,created_at TEXT NOT NULL,file_path TEXT,checklist_path TEXT,package_path TEXT)''')
    c.commit(); return c


def now(): return datetime.now().isoformat(timespec='seconds')
def safe(s): return ''.join(ch if ch.isalnum() or ch in '-_ .' else '_' for ch in str(s or '').strip()).replace(' ', '_') or 'Document'

def hash_password(p):
    salt = secrets.token_bytes(16); d = hashlib.pbkdf2_hmac('sha256', p.encode(), salt, 200000)
    return salt.hex() + '$' + d.hex()

def verify_password(p, stored):
    try:
        salt, d = stored.split('$', 1)
        got = hashlib.pbkdf2_hmac('sha256', p.encode(), bytes.fromhex(salt), 200000)
        return secrets.compare_digest(got.hex(), d)
    except Exception:
        return False

def new_token(email):
    t = secrets.token_urlsafe(32)  # never expires -> user stays logged in
    with db() as c: c.execute('INSERT INTO tokens VALUES(?,?,?)', (t, email, now()))
    return t

def me(authorization: str = Header('')):
    with db() as c:
        r = c.execute('SELECT email FROM tokens WHERE token=?', (authorization.replace('Bearer ', ''),)).fetchone()
    if not r: raise HTTPException(401, 'Login required')
    return r['email']


class Auth(BaseModel):
    email: str
    password: str


@app.post('/signup')
def signup(a: Auth):
    e = a.email.strip().lower()
    if '@' not in e or len(a.password) < 6:
        raise HTTPException(400, 'Valid email and 6+ character password required.')
    try:
        with db() as c: c.execute('INSERT INTO users VALUES(?,?,?)', (e, hash_password(a.password), now()))
    except sqlite3.IntegrityError:
        raise HTTPException(400, 'This email is already registered.')
    return {'token': new_token(e)}


@app.post('/login')
def login(a: Auth):
    e = a.email.strip().lower()
    with db() as c: r = c.execute('SELECT password_hash FROM users WHERE email=?', (e,)).fetchone()
    if not (r and verify_password(a.password, r['password_hash'])):
        raise HTTPException(400, 'Email or password is incorrect.')
    return {'token': new_token(e)}


@app.get('/equipment')
def equipment(u=Depends(me)): return list(EQUIPMENT_SHEETS)


@lru_cache(maxsize=None)
def _tasks(eq): return tuple(read_template_tasks(eq))  # Excel ek baar padho, phir cache


@app.get('/tasks')
def tasks(equipment: str, u=Depends(me)): return list(_tasks(equipment))


async def save_img(f, path):
    if f is None: return None
    path.write_bytes(await f.read()); return path


@app.post('/wcc')
async def wcc(data: str = Form(...), before: UploadFile = File(None), after: UploadFile = File(None),
              site_sig: UploadFile = File(None), hod_sig: UploadFile = File(None), client_sig: UploadFile = File(None),
              u=Depends(me)):
    d = json.loads(data); g = lambda k: d.get(k, '')
    stamp = f'{datetime.now():%Y%m%d_%H%M%S}'
    folder = OUT / f'WCC_{safe(g("project"))}_{stamp}'; folder.mkdir(parents=True, exist_ok=True)
    package = OUT / f'WCC_PACKAGE_{safe(g("project"))}_{stamp}.zip'
    before_p = await save_img(before, folder / 'before.jpg')
    after_p = await save_img(after, folder / 'after.jpg')
    site_p = await save_img(site_sig, folder / 'site_signature.png')
    hod_p = await save_img(hod_sig, folder / 'hod_signature.png')
    client_p = await save_img(client_sig, folder / 'client_signature.png')

    selected = [x.strip() for x in g('equipment').split(',') if x.strip()]
    details = g('details').strip()
    if not details:
        parts = []
        for eq in selected:
            parts.append(f'{eq}:'); parts.extend(read_template_tasks(eq))
        details = '\n'.join(parts)

    out = folder / 'WCC.docx'
    try:
        create_wcc_from_template(
            g('job'), g('client'), g('project'), g('location'), g('tel'), details, g('completion'),
            site_p, g('site_name'), g('site_date'), g('site_id'),
            hod_p, g('hod_name'), g('hod_date'), g('hod_id'),
            d.get('docs', ['Job Completion']), client_p, g('client_name'), g('client_phone'),
            d.get('satisfaction', '3. Good'), g('remarks'), g('client_sign_date'),
            out, before_p, after_p, d.get('ppm_number'), d.get('ppm_year'))
    except Exception as e:
        raise HTTPException(500, f'WCC error: {e}')

    ppm = d.get('mode') == 'PPM WCC'; cl = folder / 'Checklist.xlsx'
    if ppm: copy_selected_equipment_workbook(selected, cl)
    zipit(folder, package)
    with db() as c:
        cur = c.execute('INSERT INTO records(email,kind,project,equipment,number,created_at,file_path,checklist_path,package_path) VALUES(?,?,?,?,?,?,?,?,?)',
                        (u, d.get('mode', 'Normal WCC'), g('project'), ', '.join(selected), d.get('ppm_number') if ppm else g('job'), now(), str(out), str(cl) if ppm else '', str(package)))
    return {'id': cur.lastrowid}


def zipit(folder, package):
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob('*'):
            if p.is_file(): z.write(p, p.relative_to(folder))


@app.get('/records')
def records(u=Depends(me)):
    with db() as c:
        rows = c.execute("SELECT id,kind,project,equipment,number,created_at,(checklist_path<>'') AS has_cl FROM records WHERE email=? ORDER BY id DESC", (u,)).fetchall()
    return [dict(r) for r in rows]


@app.get('/records/{rid}/{field}')
def download(rid: int, field: str, u=Depends(me)):
    col = {'package': 'package_path', 'file': 'file_path', 'checklist': 'checklist_path'}.get(field)
    if not col: raise HTTPException(404, 'Unknown file')
    with db() as c: r = c.execute(f'SELECT {col} AS p FROM records WHERE id=? AND email=?', (rid, u)).fetchone()
    if not r or not r['p'] or not Path(r['p']).exists(): raise HTTPException(404, 'File not found')
    return FileResponse(r['p'], filename=Path(r['p']).name)


@app.get('/checklists')
def checklists(u=Depends(me)): return sorted(p.stem for p in CL.glob('*.xlsx'))


@app.post('/checklists')
async def add_checklist(building: str = Form(...), file: UploadFile = File(...), u=Depends(me)):
    (CL / (safe(building) + '.xlsx')).write_bytes(await file.read()); return {'ok': True}


@app.post('/ppm')
def ppm(d: dict, u=Depends(me)):
    g = lambda k: d.get(k, ''); sel = d['equipment']
    stamp = f'{datetime.now():%Y%m%d_%H%M%S}'
    folder = OUT / f'PPM_{safe(g("project"))}_{stamp}'; folder.mkdir(parents=True, exist_ok=True)
    main, cl = folder / 'PPM.xlsx', folder / 'Checklist.xlsx'
    package = OUT / f'PPM_PACKAGE_{safe(g("project"))}_{stamp}.zip'
    td = {e: read_template_tasks(e) for e in sel}; st, rm, fo = {}, {}, {}
    for it in d.get('items', []):
        e, i = it['eq'], it['i']
        st[(e, i)] = it['ok']; st[(e, f'no_{i}')] = it['no']; rm[(e, i)] = it['rem']; fo[(e, i)] = it['fol']
    try:
        create_ppm_package(sel, g('project'), g('location'), g('unit'), g('frequency'), g('category'),
                           int(g('fiscal_year') or datetime.now().year), g('wo'), g('ppm_number'), g('month'),
                           g('service_date'), g('start'), g('finish'), td, st, rm, fo,
                           g('technician'), g('engineer'), g('summary'), main)
        copy_selected_equipment_workbook(sel, cl)
    except Exception as e:
        raise HTTPException(500, f'PPM error: {e}')
    zipit(folder, package)
    with db() as c:
        cur = c.execute('INSERT INTO records(email,kind,project,equipment,number,created_at,file_path,checklist_path,package_path) VALUES(?,?,?,?,?,?,?,?,?)',
                        (u, 'PPM', g('project'), ', '.join(sel), g('ppm_number'), now(), str(main), str(cl), str(package)))
    return {'id': cur.lastrowid}

# NOTE: koi delete endpoint nahi hai -> records kabhi delete nahi hote.
