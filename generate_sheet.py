from pathlib import Path
import shutil
import openpyxl
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

BASE_DIR = Path(__file__).resolve().parent

def _first_existing(*paths):
    for p in paths:
        if p.exists():
            return p
    return paths[0]

EXCEL_3 = _first_existing(BASE_DIR / 'All-3.xlsx', BASE_DIR / 'templates' / 'All-3.xlsx')
EXCEL_1 = _first_existing(BASE_DIR / 'All.xlsx', BASE_DIR / 'templates' / 'All.xlsx')
WCC_TEMPLATE = _first_existing(
    BASE_DIR / '08 -EIFMEN08 - Work Completion Certificate.docx',
    BASE_DIR / 'wcc.docx',
    BASE_DIR / 'templates' / '08 -EIFMEN08 - Work Completion Certificate.docx',
    BASE_DIR / 'templates' / 'EIFMEN08_WCC_Template.docx',
)


def _sheet_names(path):
    if not path.exists():
        return []
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


EQUIPMENT_SHEETS = []
for _p in (EXCEL_3, EXCEL_1):
    for _s in _sheet_names(_p):
        if _s not in EQUIPMENT_SHEETS:
            EQUIPMENT_SHEETS.append(_s)


def _source_for_equipment(equipment):
    for p in (EXCEL_3, EXCEL_1):
        if p.exists() and equipment in _sheet_names(p):
            return p
    raise FileNotFoundError(f'Equipment sheet not found: {equipment}')


def read_template_tasks(equipment):
    src = _source_for_equipment(equipment)
    wb = openpyxl.load_workbook(src, data_only=False)
    try:
        ws = wb[equipment]
        _, rows = _find_checklist_rows(ws)
        return [str(ws.cell(r, 2).value) for r in rows if ws.cell(r, 2).value]
    finally:
        wb.close()


def _find_checklist_rows(ws):
    header_row = None
    for r in range(1, ws.max_row + 1):
        if str(ws.cell(r, 1).value or '').strip().lower() == 'sl. no.':
            header_row = r
            break
    if header_row is None:
        return None, []
    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        a = ws.cell(r, 1).value
        b = ws.cell(r, 2).value
        if isinstance(a, (int, float)) and b:
            rows.append(r)
        elif str(a or '').strip().upper().startswith('GENERAL NOTICE'):
            break
    return header_row, rows


def copy_checklist_workbook(source_path, equipment, output_path):
    """Copy an uploaded/original workbook and, when equipment is supplied, retain only that sheet."""
    source_path = Path(source_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, output_path)
    if not equipment:
        return output_path
    wb = openpyxl.load_workbook(output_path)
    try:
        if equipment not in wb.sheetnames:
            return output_path
        for name in list(wb.sheetnames):
            if name != equipment:
                del wb[name]
        wb.save(output_path)
    finally:
        wb.close()
    return output_path


def create_ppm_from_template(
    equipment, project, location, unit, frequency, category, fiscal_year,
    wo_number, ppm_number, scheduled_month, service_date, time_start, time_finish,
    tasks, statuses, remarks, followups, technician, engineer, summary,
    output_path,
):
    src = _source_for_equipment(equipment)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, output_path)
    wb = openpyxl.load_workbook(output_path)
    try:
        ws = wb[equipment]
        for name in list(wb.sheetnames):
            if name != equipment:
                del wb[name]
        ws['C3'] = project
        ws['C4'] = location
        ws['C5'] = unit
        ws['C6'] = frequency
        ws['C7'] = category
        ws['C8'] = equipment
        ws['K3'] = fiscal_year
        ws['K4'] = wo_number
        ws['K5'] = scheduled_month
        ws['K6'] = service_date
        ws['K7'] = time_start
        ws['K8'] = time_finish
        # Add PPM number only where the supplied template already contains a label.
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and 'PPM Number' in cell.value:
                    ws.cell(cell.row, cell.column + 1).value = ppm_number
        _, source_rows = _find_checklist_rows(ws)
        statuses, remarks, followups = statuses or {}, remarks or {}, followups or {}
        for idx, r in enumerate(source_rows, start=1):
            ws.cell(r, 7).value = '✓' if statuses.get(idx) else ''
            ws.cell(r, 8).value = '✓' if statuses.get(f'no_{idx}') else ''
            ws.cell(r, 9).value = remarks.get(idx, '')
            ws.cell(r, 11).value = followups.get(idx, '')
            if idx <= len(tasks or []):
                ws.cell(r, 2).value = tasks[idx - 1]
        for r in range(1, ws.max_row + 1):
            a = str(ws.cell(r, 1).value or '')
            if a.startswith('Tech. Date/Sign:') and technician:
                ws.cell(r, 1).value = f'Tech. Date/Sign: {technician}'
            if a.startswith('Eng./Sup Date Sign') and engineer:
                ws.cell(r, 1).value = f'Eng./Sup Date Sign : {engineer}'
            if a.startswith('REPORT SUMMARY') and summary and r + 1 <= ws.max_row:
                ws.cell(r + 1, 1).value = summary
        wb.save(output_path)
    finally:
        wb.close()
    return output_path


def _set_paragraph(p, text, size=9):
    p.text = text
    for run in p.runs:
        run.font.size = Pt(size)


def _find_para(doc, needle):
    for i, p in enumerate(doc.paragraphs):
        if needle.lower() in p.text.lower():
            return i
    return None


def _insert_picture_after_paragraph(paragraph, image_path, width=6.0):
    # python-docx has no public insert-after API; move a newly-created paragraph
    # immediately after the target paragraph.
    new_p = OxmlElement('w:p')
    paragraph._p.addnext(new_p)
    from docx.text.paragraph import Paragraph
    new_para = Paragraph(new_p, paragraph._parent)
    new_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = new_para.add_run()
    run.add_picture(str(image_path), width=Inches(width))
    return new_para


def create_wcc_from_template(
    job_order, client, project, location, tel, details, completion,
    site_sig, site_name, site_date, site_id,
    hod_sig, hod_name, hod_date, hod_id,
    docs, client_sig, client_name, client_phone, satisfaction,
    remarks, client_sign_date, output_path,
    before_image=None, after_image=None, ppm_number=None, ppm_year=None,
):
    if not WCC_TEMPLATE.exists():
        raise FileNotFoundError(f'WCC template not found: {WCC_TEMPLATE}')
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document(WCC_TEMPLATE)

    # The supplied DOCX is the PPM-filled example. For normal WCC we blank the
    # PPM example in the Job Order field; for PPM WCC we replace it dynamically.
    if ppm_number:
        jo_text = f'{ppm_number} PPM Service Year {ppm_year or ""}'.strip()
    else:
        jo_text = job_order or ''

    replacements = {
        4: f'Job Order Number  :- {jo_text}',
        5: f'Client                         :- {client}',
        6: f'Project                       :- {project}',
        7: f'Location                     :- {location}                            Tel. No. :- {tel}',
        15: f'Date & Time of Completion :- {completion}',
        17: f'Signature of Site in Charge:- {site_sig}    Name :- {site_name}    Date :- {site_date}',
        18: f'  ID : - {site_id}',
        19: f'8.  Signature of HOD :- {hod_sig}    Name:- {hod_name}    Date :- {hod_date}    ID :- {hod_id}',
        24: f' Client Signature:- {client_sig}',
        26: f'Name: - {client_name}',
        28: f'Phone No. :- {client_phone}',
        39: f'Client Signature  ---------------------    Date :- {client_sign_date}',
    }
    for idx, value in replacements.items():
        if idx < len(doc.paragraphs):
            _set_paragraph(doc.paragraphs[idx], value)

    lines = [x.strip() for x in (details or '').splitlines() if x.strip()]
    for idx in range(9, 15):
        if idx < len(doc.paragraphs):
            _set_paragraph(doc.paragraphs[idx], lines[idx - 9] if idx - 9 < len(lines) else '')

    selected = set(docs or [])
    if len(doc.paragraphs) > 21:
        labels = ['LPO', 'Invoice', 'Delivery Note', 'Petty Cash']
        _set_paragraph(doc.paragraphs[21], '   '.join(f"{'☑' if x in selected else '☐'} {x}" for x in labels))
    if len(doc.paragraphs) > 23:
        labels = ['Material Requisition', 'Job Completion']
        _set_paragraph(doc.paragraphs[23], '   '.join(f"{'☑' if x in selected else '☐'} {x}" for x in labels))

    for p in doc.paragraphs:
        if 'Dear valued customer' in p.text:
            _set_paragraph(p, p.text + f'   Selected: {satisfaction}')
        if p.text.strip() == 'Remarks /Suggestions:':
            _set_paragraph(p, p.text + f' {remarks or ""}')

    # Normal WCC only: add before/after photos after the front-page content.
    if before_image or after_image:
        tail = doc.paragraphs[39] if len(doc.paragraphs) > 39 else doc.paragraphs[-1]
        if before_image:
            p = _insert_picture_after_paragraph(tail, before_image)
            cap = OxmlElement('w:p'); tail._p.addnext(cap)
            from docx.text.paragraph import Paragraph
            cp = Paragraph(cap, tail._parent); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER; cp.add_run('Before Picture')
            tail = p
        if after_image:
            p = _insert_picture_after_paragraph(tail, after_image)
            cap = OxmlElement('w:p'); tail._p.addnext(cap)
            from docx.text.paragraph import Paragraph
            cp = Paragraph(cap, tail._parent); cp.alignment = WD_ALIGN_PARAGRAPH.CENTER; cp.add_run('After Picture')

    doc.save(output_path)
    return output_path


# Backward-compatible wrappers.
def generate_ppm(source, equipment, meta, out):
    return create_ppm_from_template(
        equipment, meta.get('project',''), meta.get('location',''), meta.get('unit',''),
        meta.get('frequency',''), meta.get('category',''), meta.get('fiscal_year',''),
        meta.get('wo',''), meta.get('ppm','1st PPM'), meta.get('month',''), meta.get('service_date',''),
        meta.get('time_start',''), meta.get('time_finish',''), meta.get('tasks',[]),
        meta.get('statuses',{}), meta.get('remarks',{}), meta.get('followups',{}),
        meta.get('technician',''), meta.get('engineer',''), meta.get('summary',''), out)


def generate_wcc(template, meta, out):
    return create_wcc_from_template(
        meta.get('job',''), meta.get('client',''), meta.get('project',''), meta.get('location',''),
        meta.get('tel',''), meta.get('details',''), meta.get('completion',''),
        meta.get('site_sig',''), meta.get('site',''), meta.get('site_date',''), meta.get('siteid',''),
        meta.get('hod_sig',''), meta.get('hod',''), meta.get('hod_date',''), meta.get('hodid',''),
        meta.get('docs',[]), meta.get('client_sig',''), meta.get('cname',''), meta.get('phone',''),
        meta.get('satisfaction',''), meta.get('remarks',''), meta.get('client_sign_date',''), out)
