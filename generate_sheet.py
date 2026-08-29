from pathlib import Path
import shutil
import openpyxl
from docx import Document
from docx.shared import Pt

BASE_DIR = Path(__file__).resolve().parent

# The project is intentionally root-upload friendly. We also support the
# templates/ and assets/ layout if someone later creates those folders.
def _first_existing(*paths):
    for p in paths:
        if p.exists():
            return p
    return paths[0]

EXCEL_3 = _first_existing(BASE_DIR / "All-3.xlsx", BASE_DIR / "templates" / "All-3.xlsx")
EXCEL_1 = _first_existing(BASE_DIR / "All.xlsx", BASE_DIR / "templates" / "All.xlsx")
WCC_TEMPLATE = _first_existing(
    BASE_DIR / "08 -EIFMEN08 - Work Completion Certificate.docx",
    BASE_DIR / "EIFMEN08_WCC_Template.docx",
    BASE_DIR / "templates" / "08 -EIFMEN08 - Work Completion Certificate.docx",
    BASE_DIR / "templates" / "EIFMEN08_WCC_Template.docx",
)


def _sheet_names(path: Path):
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
    raise FileNotFoundError(f"Equipment sheet not found: {equipment}")


def read_template_tasks(equipment):
    src = _source_for_equipment(equipment)
    wb = openpyxl.load_workbook(src, data_only=False)
    try:
        ws = wb[equipment]
        header_row = None
        for r in range(1, ws.max_row + 1):
            if str(ws.cell(r, 1).value or "").strip().lower() == "sl. no.":
                header_row = r
                break
        if header_row is None:
            return []
        tasks = []
        for r in range(header_row + 1, ws.max_row + 1):
            a = ws.cell(r, 1).value
            b = ws.cell(r, 2).value
            if isinstance(a, int) and b:
                tasks.append(str(b))
            elif isinstance(a, float) and a.is_integer() and b:
                tasks.append(str(b))
            elif str(a or "").strip().upper().startswith("GENERAL NOTICE"):
                break
        return tasks
    finally:
        wb.close()


def _find_checklist_rows(ws):
    header_row = None
    for r in range(1, ws.max_row + 1):
        if str(ws.cell(r, 1).value or "").strip().lower() == "sl. no.":
            header_row = r
            break
    if header_row is None:
        raise ValueError("Could not locate checklist header in the supplied sheet.")

    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        a = ws.cell(r, 1).value
        b = ws.cell(r, 2).value
        if isinstance(a, (int, float)) and b:
            rows.append(r)
        elif str(a or "").strip().upper().startswith("GENERAL NOTICE"):
            break
    return header_row, rows


def create_ppm_from_template(
    equipment, project, location, unit, frequency, category, fiscal_year,
    wo_number, ppm_number, scheduled_month, service_date, time_start, time_finish,
    tasks, statuses, remarks, followups, technician, engineer, summary,
    output_path,
):
    src = _source_for_equipment(equipment)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy the original workbook, then retain ONLY the selected original
    # equipment worksheet. No new blue table/design is created.
    shutil.copy2(src, output_path)
    wb = openpyxl.load_workbook(output_path)
    try:
        if equipment not in wb.sheetnames:
            raise ValueError(f"Equipment sheet not found: {equipment}")
        ws = wb[equipment]
        for name in list(wb.sheetnames):
            if name != equipment:
                del wb[name]

        # Supplied workbook input cells.
        ws["C3"] = project
        ws["C4"] = location
        ws["C5"] = unit
        ws["C6"] = frequency
        ws["C7"] = category
        ws["C8"] = equipment
        ws["K3"] = fiscal_year
        ws["K4"] = wo_number
        ws["K5"] = scheduled_month
        ws["K6"] = service_date
        ws["K7"] = time_start
        ws["K8"] = time_finish

        # Put the PPM number in the first suitable header cell without changing
        # the sheet structure. If the source does not have a PPM label, we leave
        # the original layout untouched.
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and "PPM Number" in cell.value:
                    target = ws.cell(cell.row, cell.column + 1)
                    target.value = ppm_number
                    break

        _, source_rows = _find_checklist_rows(ws)
        statuses = statuses or {}
        remarks = remarks or {}
        followups = followups or {}

        for idx, r in enumerate(source_rows, start=1):
            ok = bool(statuses.get(idx, False))
            not_ok = bool(statuses.get(f"no_{idx}", False))
            ws.cell(r, 7).value = "✓" if ok else ""
            ws.cell(r, 8).value = "✓" if not_ok else ""
            ws.cell(r, 9).value = remarks.get(idx, "")
            ws.cell(r, 11).value = followups.get(idx, "")
            if idx <= len(tasks or []):
                ws.cell(r, 2).value = tasks[idx - 1]

        # Preserve existing signature/summary locations when those labels exist.
        for r in range(1, ws.max_row + 1):
            a = str(ws.cell(r, 1).value or "")
            if a.startswith("Tech. Date/Sign:") and technician:
                ws.cell(r, 1).value = f"Tech. Date/Sign: {technician}"
            if a.startswith("Eng./Sup Date Sign") and engineer:
                ws.cell(r, 1).value = f"Eng./Sup Date Sign : {engineer}"
            if a.startswith("REPORT SUMMARY") and summary and r + 1 <= ws.max_row:
                ws.cell(r + 1, 1).value = summary

        wb.save(output_path)
    finally:
        wb.close()
    return output_path


def _replace_all_paragraph_text(doc, old, new):
    changed = False
    for p in doc.paragraphs:
        if old in p.text:
            p.text = p.text.replace(old, new)
            changed = True
    return changed


def _set_paragraph(p, text):
    p.text = text
    if p.runs:
        for run in p.runs:
            run.font.size = Pt(9)


def create_wcc_from_template(
    job_order, client, project, location, tel, details, completion,
    site_sig, site_name, site_date, site_id,
    hod_sig, hod_name, hod_date, hod_id,
    docs, client_sig, client_name, client_phone, satisfaction,
    remarks, client_sign_date, output_path,
):
    if not WCC_TEMPLATE.exists():
        raise FileNotFoundError(f"WCC template not found: {WCC_TEMPLATE}")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = Document(WCC_TEMPLATE)

    # Work directly against the exact supplied paragraph positions/text.
    replacements = {
        4: f"Job Order Number  :- {job_order}",
        5: f"Client                         :- {client}",
        6: f"Project                       :- {project}",
        7: f"Location                     :- {location}                            Tel. No. :- {tel}",
        15: f"Date & Time of Completion :- {completion}",
        17: f"Signature of Site in Charge:- {site_sig}    Name :- {site_name}    Date :- {site_date}",
        18: f"  ID : - {site_id}",
        19: f"8.  Signature of HOD :- {hod_sig}    Name:- {hod_name}    Date :- {hod_date}    ID :- {hod_id}",
        24: f" Client Signature:- {client_sig}",
        26: f"Name: - {client_name}",
        28: f"Phone No. :- {client_phone}",
        39: f"Client Signature  ---------------------    Date :- {client_sign_date}",
    }
    for idx, value in replacements.items():
        if idx < len(doc.paragraphs):
            _set_paragraph(doc.paragraphs[idx], value)

    # Details occupy the six dedicated lines in the supplied form.
    lines = [x.strip() for x in (details or "").splitlines() if x.strip()]
    for idx in range(9, 15):
        if idx < len(doc.paragraphs):
            _set_paragraph(doc.paragraphs[idx], lines[idx - 9] if idx - 9 < len(lines) else "")

    # Preserve the document wording/order while replacing only the checkbox lines.
    selected = set(docs or [])
    if len(doc.paragraphs) > 21:
        labels = ["LPO", "Invoice", "Delivery Note", "Petty Cash"]
        _set_paragraph(doc.paragraphs[21], "   ".join(f"{'☑' if x in selected else '☐'} {x}" for x in labels))
    if len(doc.paragraphs) > 23:
        labels = ["Material Requisition", "Job Completion"]
        _set_paragraph(doc.paragraphs[23], "   ".join(f"{'☑' if x in selected else '☐'} {x}" for x in labels))

    # Satisfaction and remarks stay near their original labels.
    for p in doc.paragraphs:
        if "Dear valued customer" in p.text:
            p.text = p.text + f"   Selected: {satisfaction}"
        if p.text.strip() == "Remarks /Suggestions:":
            p.text = p.text + f" {remarks or ''}"

    doc.save(output_path)
    return output_path


# Backward-compatible names used by older copies of the project.
def generate_ppm(source, equipment, meta, out):
    return create_ppm_from_template(
        equipment=equipment,
        project=meta.get("project", ""), location=meta.get("location", ""),
        unit=meta.get("unit", ""), frequency=meta.get("frequency", ""),
        category=meta.get("category", ""), fiscal_year=meta.get("fiscal_year", ""),
        wo_number=meta.get("wo", ""), ppm_number=meta.get("ppm", "1st PPM"),
        scheduled_month=meta.get("month", ""),
        service_date=meta.get("service_date", ""),
        time_start=meta.get("time_start", ""), time_finish=meta.get("time_finish", ""),
        tasks=meta.get("tasks", []), statuses=meta.get("statuses", {}),
        remarks=meta.get("remarks", {}), followups=meta.get("followups", {}),
        technician=meta.get("technician", ""), engineer=meta.get("engineer", ""),
        summary=meta.get("summary", ""), output_path=out,
    )


def generate_wcc(template, meta, out):
    return create_wcc_from_template(
        job_order=meta.get("job", ""), client=meta.get("client", ""),
        project=meta.get("project", ""), location=meta.get("location", ""),
        tel=meta.get("tel", ""), details=meta.get("details", ""), completion=meta.get("completion", ""),
        site_sig=meta.get("site_sig", ""), site_name=meta.get("site", ""), site_date=meta.get("site_date", ""), site_id=meta.get("siteid", ""),
        hod_sig=meta.get("hod_sig", ""), hod_name=meta.get("hod", ""), hod_date=meta.get("hod_date", ""), hod_id=meta.get("hodid", ""),
        docs=meta.get("docs", []), client_sig=meta.get("client_sig", ""), client_name=meta.get("cname", ""),
        client_phone=meta.get("phone", ""), satisfaction=meta.get("satisfaction", ""),
        remarks=meta.get("remarks", ""), client_sign_date=meta.get("client_sign_date", ""), output_path=out,
    )
