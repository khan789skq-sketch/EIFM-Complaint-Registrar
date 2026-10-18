import hashlib, json, secrets, sqlite3, zipfile, os, uuid, shutil, subprocess, tempfile
from contextlib import asynccontextmanager
from functools import lru_cache
from starlette.concurrency import run_in_threadpool
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from wcc_pdf import make_wcc_pdf
from generate_sheet import (EQUIPMENT_SHEETS, create_wcc_from_template, create_ppm_package,
                            read_template_tasks, copy_selected_equipment_workbook)

BASE = Path(__file__).resolve().parent
DATA = Path(os.environ.get('EIFM_DATA_DIR', '/data' if Path('/data').is_dir() else str(BASE / 'data')))
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / 'outputs'; OUT.mkdir(parents=True, exist_ok=True)
CL = DATA / 'building_checklists'; CL.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA / 'eifm_app.db'
@asynccontextmanager
async def lifespan(application):
    # A startup backup helps recovery; it is NOT a substitute for off-server backups.
    if DB_PATH.exists():
        backup_dir = DATA / 'backups'
        backup_dir.mkdir(exist_ok=True)
        with sqlite3.connect(DB_PATH) as src, sqlite3.connect(backup_dir / 'eifm_latest.db') as dest:
            src.backup(dest)
    yield

app = FastAPI(lifespan=lifespan)



def db():
    c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    c.execute('PRAGMA busy_timeout=30000')
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('CREATE TABLE IF NOT EXISTS users(email TEXT PRIMARY KEY,password_hash TEXT NOT NULL,created_at TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS tokens(token TEXT PRIMARY KEY,email TEXT NOT NULL,created_at TEXT NOT NULL)')
    c.execute('''CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY AUTOINCREMENT,email TEXT NOT NULL,kind TEXT NOT NULL,project TEXT,equipment TEXT,number TEXT,created_at TEXT NOT NULL,file_path TEXT,checklist_path TEXT,package_path TEXT)''')
    c.commit(); return c


def now(): return datetime.now().isoformat(timespec='seconds')
def unique_stamp(): return f'{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:12]}'
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
    allowed = {'.jpg', '.jpeg', '.png', '.webp'}
    if path.suffix.lower() not in allowed: raise HTTPException(400, 'Invalid image extension')
    max_size = 12 * 1024 * 1024
    size = 0
    with path.open('wb') as dest:
        while chunk := await f.read(1024 * 1024):
            size += len(chunk)
            if size > max_size:
                dest.close(); path.unlink(missing_ok=True)
                raise HTTPException(413, 'Image must be smaller than 12 MB')
            dest.write(chunk)
    return path


@app.post('/wcc')
async def wcc(data: str = Form(...), before: UploadFile = File(None), after: UploadFile = File(None),
              site_sig: UploadFile = File(None), hod_sig: UploadFile = File(None), client_sig: UploadFile = File(None),
              u=Depends(me)):
    d = json.loads(data); g = lambda k: d.get(k, '')
    stamp = unique_stamp()
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
    if not ppm:
        try:
            make_wcc_pdf(d, before_p, after_p, folder / 'WCC.pdf', site_p, hod_p, client_p)
        except Exception as e:
            raise HTTPException(500, f'WCC PDF error: {e}')
    if ppm:
        try:
            copy_selected_equipment_workbook(selected, cl)
            make_wcc_pdf(d, None, None, folder / 'PPM_WCC.pdf', site_p, hod_p, client_p)
            attach_ppm_excel_pages(folder / 'PPM_WCC.pdf', cl)
        except Exception as e:
            raise HTTPException(500, f'PPM WCC PDF error: {e}')
    zipit(folder, package)
    with db() as c:
        cur = c.execute('INSERT INTO records(email,kind,project,equipment,number,created_at,file_path,checklist_path,package_path) VALUES(?,?,?,?,?,?,?,?,?)',
                        (u, d.get('mode', 'Normal WCC'), g('project'), ', '.join(selected), d.get('ppm_number') if ppm else g('job'), now(), str(out), str(cl) if ppm else '', str(package)))
    return {'id': cur.lastrowid}




# ---------- Multiple NORMAL WCC package (existing /wcc generation is unchanged) ----------
class NormalWccBatchRequest(BaseModel):
    ids: list[int]


@app.post('/wcc-batch/package')
def normal_wcc_batch_package(request: NormalWccBatchRequest, u=Depends(me)):
    """Bundle previously generated Normal WCCs into one downloadable ZIP.

    Each complaint is created by the unchanged /wcc endpoint. The batch screen
    uploads one at a time, which avoids huge photo uploads and allows resuming.
    No arbitrary number-of-complaints limit is imposed here.
    """
    ids = list(dict.fromkeys(request.ids))
    if not ids:
        raise HTTPException(400, 'Select at least one Normal WCC')
    if any(not isinstance(rid, int) or rid <= 0 for rid in ids):
        raise HTTPException(400, 'Invalid Normal WCC record number')
    # Use fixed-size query parameters per record; no SQLite IN-clause cap.
    with db() as conn:
        by_id = {}
        for rid in ids:
            record = conn.execute(
                'SELECT id, kind, number, package_path FROM records '
                'WHERE email=? AND id=?', (u, rid),
            ).fetchone()
            if record is not None:
                by_id[rid] = dict(record)
    for rid in ids:
        record = by_id.get(rid)
        if record is None:
            raise HTTPException(404, f'Normal WCC record {rid} not found')
        if record['kind'] != 'Normal WCC':
            raise HTTPException(400, f'Record {rid} is not a Normal WCC')
        if not record['package_path'] or not Path(record['package_path']).is_file():
            raise HTTPException(404, f'ZIP for Normal WCC record {rid} is missing')

    package = OUT / f'EIFM_Normal_WCC_Batch_{unique_stamp()}.zip'
    try:
        with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as target:
            for position, rid in enumerate(ids, 1):
                record = by_id[rid]
                # Each report keeps its OWN WCC.pdf, WCC.docx, Before/After and signatures.
                prefix = f'{position:04d}_{safe(record["number"] or f"WCC_{rid}")}'
                with zipfile.ZipFile(record['package_path'], 'r') as original:
                    for member in original.infolist():
                        if member.is_dir():
                            continue
                        rel = Path(member.filename)
                        if rel.is_absolute() or '..' in rel.parts:
                            raise ValueError('Unsafe filename in existing WCC package')
                        with original.open(member, 'r') as source:
                            with target.open(f'{prefix}/{rel.as_posix()}', 'w', force_zip64=True) as out:
                                shutil.copyfileobj(source, out, 1024 * 1024)
    except Exception:
        package.unlink(missing_ok=True)
        raise

    # Do not accumulate one-off combined batch ZIPs on the Render filesystem.
    from starlette.background import BackgroundTask
    return FileResponse(
        package, filename=package.name, media_type='application/zip',
        background=BackgroundTask(lambda: package.unlink(missing_ok=True)),
    )


def attach_ppm_excel_pages(wcc_pdf: Path, excel_path: Path):
    """Append the selected equipment sheets to the existing PPM WCC PDF.

    The source WCC PDF and XLSX are not modified. Conversion uses LibreOffice's
    native spreadsheet PDF export so sheet print settings and styling are retained.
    """
    from pypdf import PdfReader, PdfWriter

    wcc_pdf, excel_path = Path(wcc_pdf), Path(excel_path)
    if not wcc_pdf.is_file() or not excel_path.is_file():
        raise FileNotFoundError('PPM WCC PDF or selected equipment workbook is missing')
    with tempfile.TemporaryDirectory(prefix='eifm_ppm_') as tmp:
        tmp = Path(tmp)
        profile = (tmp / 'lo_profile').as_uri()
        try:
            result = subprocess.run(
                ['libreoffice', f'-env:UserInstallation={profile}', '--headless',
                 '--convert-to', 'pdf:calc_pdf_Export', '--outdir', str(tmp), str(excel_path)],
                capture_output=True, text=True, timeout=240, check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError('LibreOffice is required on the backend server for PPM checklist PDF attachment') from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('PPM Excel-to-PDF conversion timed out') from exc
        checklist_pdf = tmp / (excel_path.stem + '.pdf')
        if result.returncode != 0 or not checklist_pdf.is_file():
            raise RuntimeError('PPM checklist PDF conversion failed: ' + (result.stderr or result.stdout)[-600:])
        writer = PdfWriter()
        for source in (wcc_pdf, checklist_pdf):
            reader = PdfReader(str(source))
            if len(reader.pages) == 0:
                raise RuntimeError('PPM PDF has no pages: ' + source.name)
            for page in reader.pages:
                writer.add_page(page)
        combined = tmp / 'PPM_WCC_combined.pdf'
        with combined.open('wb') as stream:
            writer.write(stream)
        # Replace only after successful conversion and merge.
        shutil.copyfile(combined, wcc_pdf)
    return wcc_pdf


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
    if not file.filename or not file.filename.lower().endswith('.xlsx'):
        raise HTTPException(400, 'Only .xlsx checklist files are supported')
    if not building.strip(): raise HTTPException(400, 'Building name required')
    destination = CL / (safe(building) + '.xlsx')
    temporary = destination.with_name(destination.name + '.' + uuid.uuid4().hex + '.tmp')
    total = 0
    try:
        with temporary.open('wb') as output:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > 25 * 1024 * 1024: raise HTTPException(413, 'Checklist maximum is 25 MB')
                output.write(chunk)
        # Verify this is a real Excel workbook before replacing an existing building checklist.
        from openpyxl import load_workbook
        workbook = load_workbook(temporary, read_only=True)
        workbook.close()
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return {'ok': True}


@app.post('/ppm')
def ppm(d: dict, u=Depends(me)):
    # Existing JSON API retained for backwards compatibility.
    return _generate_ppm(d, u)


@app.post('/ppm-with-signatures')
async def ppm_with_signatures(data: str = Form(...),
                              site_sig: UploadFile = File(None),
                              hod_sig: UploadFile = File(None),
                              client_sig: UploadFile = File(None),
                              u=Depends(me)):
    # Used ONLY by New PPM; the original /wcc endpoint is untouched.
    try:
        d = json.loads(data)
        if not isinstance(d, dict):
            raise ValueError('Expected an object')
    except (ValueError, TypeError):
        raise HTTPException(400, 'Invalid PPM data')
    with tempfile.TemporaryDirectory(prefix='eifm_ppm_signatures_') as tmp:
        p = Path(tmp)
        paths = []
        for f, filename in ((site_sig, 'site_signature.png'),
                            (hod_sig, 'hod_signature.png'),
                            (client_sig, 'client_signature.png')):
            paths.append(await save_img(f, p / filename) if f is not None else None)
        # Images live outside the ZIP folder; only the signed PDF + XLSX files go into ZIP.
        return await run_in_threadpool(_generate_ppm, d, u, *paths)


def _generate_ppm(d: dict, u, site_sig=None, hod_sig=None, client_sig=None):
    g = lambda k: d.get(k, ''); sel = d['equipment']
    stamp = unique_stamp()
    folder = OUT / f'PPM_{safe(g("project"))}_{stamp}'; folder.mkdir(parents=True, exist_ok=True)
    main, cl = folder / 'PPM.xlsx', folder / 'Checklist.xlsx'
    package = OUT / f'PPM_PACKAGE_{safe(g("project"))}_{stamp}.zip'
    td = {e: read_template_tasks(e) for e in sel}; st, rm, fo = {}, {}, {}
    for it in d.get('items', []):
        e, i = it['eq'], it['i']
        st[(e, i)] = it['ok']; st[(e, f'no_{i}')] = it['no']; rm[(e, i)] = it['rem']; fo[(e, i)] = it['fol']
    try:
        create_ppm_package(sel, g('project'), g('location'), g('unit'), g('frequency'), g('category'),
                           int(g('fiscal_year') or datetime.now().year), '', g('ppm_number'), g('month'),
                           g('service_date'), g('start'), g('finish'), td, st, rm, fo,
                           g('technician'), g('engineer'), g('summary'), main)
        copy_selected_equipment_workbook(sel, cl)
        # New PPM must include the SAME original WCC certificate front page,
        # in addition to the existing equipment Excel checklists.
        cert_data = {
            **d, 'mode': 'PPM WCC', 'ppm_number': g('ppm_number'),
            'ppm_year': g('fiscal_year'), 'job': g('wo'),
            'client': g('client'), 'project': g('project'),
            'location': g('location'), 'tel': g('tel'),
            'completion': g('completion') or (g('service_date') + (' ' + g('finish') if g('finish') else '')) ,
            'details': g('summary'), 'client_name': g('client_name'),
            'client_phone': g('client_phone'),
            'site_name': g('site_name'), 'site_date': g('site_date'), 'site_id': g('site_id'),
            'hod_name': g('hod_name'), 'hod_date': g('hod_date'), 'hod_id': g('hod_id'),
            'docs': d.get('docs', ['Job Completion']),
        }
        make_wcc_pdf(cert_data, out=folder / 'PPM_WCC.pdf',
                     site_sig=site_sig, hod_sig=hod_sig, client_sig=client_sig)
        # PPM.xlsx contains the completed OK/Not OK ticks, remarks and follow-ups.
        attach_ppm_excel_pages(folder / 'PPM_WCC.pdf', main)
    except Exception as e:
        raise HTTPException(500, f'PPM error: {e}')
    zipit(folder, package)
    with db() as c:
        cur = c.execute('INSERT INTO records(email,kind,project,equipment,number,created_at,file_path,checklist_path,package_path) VALUES(?,?,?,?,?,?,?,?,?)',
                        (u, 'PPM', g('project'), ', '.join(sel), g('ppm_number'), now(), str(main), str(cl), str(package)))
    return {'id': cur.lastrowid}

# NOTE: koi delete endpoint nahi hai -> records kabhi delete nahi hote.


@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/me')
def current_user(u=Depends(me)):
    return {'email': u}
