
from pathlib import Path
import shutil
import openpyxl
from openpyxl.styles import Alignment
from docx import Document

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = BASE_DIR / "templates"

# Union of equipment worksheets from BOTH supplied Excel files.
def _sheet_names(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    names = [x for x in wb.sheetnames if x.lower() != "split" or True]
    wb.close()
    return names

EQUIPMENT_SHEETS = []
for _p in [TEMPLATES / "All-3.xlsx", TEMPLATES / "All.xlsx"]:
    for _s in _sheet_names(_p):
        if _s not in EQUIPMENT_SHEETS:
            EQUIPMENT_SHEETS.append(_s)

def _source_for_equipment(equipment):
    p3 = TEMPLATES / "All-3.xlsx"
    p1 = TEMPLATES / "All.xlsx"
    if equipment in openpyxl.load_workbook(p3, read_only=True).sheetnames:
        return p3
    return p1

def read_template_tasks(equipment):
    src = _source_for_equipment(equipment)
    wb = openpyxl.load_workbook(src, data_only=False)
    ws = wb[equipment]
    header_row = None
    for r in range(1, ws.max_row + 1):
        if str(ws.cell(r,1).value or "").strip().lower() == "sl. no.":
            header_row = r
            break
    if header_row is None:
        wb.close()
        return []
    tasks = []
    for r in range(header_row + 1, ws.max_row + 1):
        a = ws.cell(r,1).value
        b = ws.cell(r,2).value
        if isinstance(a, int) and b:
            tasks.append(str(b))
        elif isinstance(a, float) and a.is_integer() and b:
            tasks.append(str(b))
        elif str(a).strip().upper().startswith("GENERAL NOTICE"):
            break
    wb.close()
    return tasks

def create_ppm_from_template(
    equipment, project, location, unit, frequency, category, fiscal_year,
    wo_number, scheduled_month, service_date, time_start, time_finish,
    tasks, statuses, remarks, followups, technician, engineer, summary,
    output_path
):
    src = _source_for_equipment(equipment)
    wb = openpyxl.load_workbook(src)
    if equipment not in wb.sheetnames:
        raise ValueError(f"Equipment sheet not found: {equipment}")
    ws = wb[equipment]

    # Remove all other sheets so the download remains the selected original sheet.
    for name in list(wb.sheetnames):
        if name != equipment:
            del wb[name]

    # These are the exact input cells in the supplied workbook layout.
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

    header_row = None
    for r in range(1, ws.max_row + 1):
        if str(ws.cell(r,1).value or "").strip().lower() == "sl. no.":
            header_row = r
            break
    if header_row is None:
        raise ValueError("Could not locate checklist header in the supplied sheet.")

    # Keep original task formatting/rows. Fill the task/status/remarks/follow-up cells.
    source_rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        a = ws.cell(r,1).value
        b = ws.cell(r,2).value
        if isinstance(a, (int,float)) and b:
            source_rows.append(r)
        elif str(a or "").strip().upper().startswith("GENERAL NOTICE"):
            break

    for idx, r in enumerate(source_rows, start=1):
        ok = bool(statuses.get(idx, False))
        not_ok = bool(statuses.get(f"no_{idx}", False))
        ws.cell(r,7).value = "✓" if ok else ""
        ws.cell(r,8).value = "✓" if not_ok else ""
        ws.cell(r,9).value = remarks.get(idx, "")
        ws.cell(r,11).value = followups.get(idx, "")

    # If the user edited task text, update only the task cells; all formatting remains from the template.
    for idx, r in enumerate(source_rows, start=1):
        if idx <= len(tasks):
            ws.cell(r,2).value = tasks[idx-1]

    # Original signature/summary positions differ slightly by template; find them by label.
    for r in range(1, ws.max_row + 1):
        a = str(ws.cell(r,1).value or "")
        if a.startswith("Tech. Date/Sign:") and technician:
            ws.cell(r,1).value = f"Tech. Date/Sign: {technician}"
        if a.startswith("Eng./Sup Date Sign") and engineer:
            ws.cell(r,1).value = f"Eng./Sup Date Sign : {engineer}"
        if a.startswith("REPORT SUMMARY") and summary:
            if r + 1 <= ws.max_row:
                ws.cell(r+1,1).value = summary

    # Preserve the original workbook's print/layout settings.
    wb.save(output_path)
    return output_path

def _replace_paragraph_text(paragraph, replacements):
    text = paragraph.text
    new_text = text
    for old, new in replacements:
        if old in new_text:
            new_text = new_text.replace(old, new)
    if new_text == text:
        return
    # Preserve paragraph-level formatting; the source template is one-page and
    # already contains the official logo/footer/design.
    paragraph.text = new_text
    for run in paragraph.runs:
        run.bold = True

def create_wcc_from_template(
    job_order, client, project, location, tel, details, completion,
    site_sig, site_name, site_date, site_id,
    hod_sig, hod_name, hod_date, hod_id,
    docs, client_sig, client_name, client_phone, satisfaction,
    remarks, client_sign_date, output_path
):
    src = TEMPLATES / "EIFMEN08_WCC_Template.docx"
    doc = Document(src)

    repl = [
        ("_2nd PPM Service Year 2026____________________", f"_{job_order}____________________________"),
        ("_East & West International_______________________________", f"_{client}_______________________________"),
        ("_Marina Gate -2_________________________________________", f"_{project}_________________________________________"),
        ("Flat - 3206____________________________Tel. No. :- _______", f"{location}____________________________Tel. No. :- {tel}"),
        ("Date & Time of Completion :- _____________________", f"Date & Time of Completion :- {completion}"),
        ("Signature of Site in Charge:- ________________Name :-___________ Date :- __________",
         f"Signature of Site in Charge:- {site_sig}    Name :- {site_name}    Date :- {site_date}"),
        ("  ID\t : -  \t", f"  ID : - {site_id}"),
        ("8.  Signature of HOD :-\t \t\t\t  Name:- _____________ Date :- _________                           \t\t   ID      :-____________________ ",
         f"8.  Signature of HOD :- {hod_sig}    Name:- {hod_name} Date :- {hod_date}    ID :- {hod_id}"),
        (" Client Signature:-  \t\t", f" Client Signature:- {client_sig}"),
        ("Name: -  \t", f"Name: - {client_name}"),
        ("Phone No. :-  \t", f"Phone No. :- {client_phone}"),
        ("Client Signature  ---------------------\tDate :- ____/____/_____",
         f"Client Signature  --------------------- Date :- {client_sign_date}"),
    ]

    # Replace exact sample values while leaving the supplied document as the base.
    for p in doc.paragraphs:
        _replace_paragraph_text(p, repl)

    # Work details occupy six dedicated lines in the supplied template.
    detail_lines = [x.strip() for x in details.splitlines() if x.strip()]
    for idx in range(9, 15):
        if idx < len(doc.paragraphs):
            value = detail_lines[idx - 9] if idx - 9 < len(detail_lines) else ""
            doc.paragraphs[idx].text = value

    # Documents: retain the official wording/order and mark selected items.
    selected = set(docs or [])
    for p in doc.paragraphs:
        if "LPO" in p.text and "Invoice" in p.text:
            labels = ["LPO", "Invoice", "Delivery Note", "Petty Cash"]
            p.text = "   ".join([f"{'☑' if x in selected else '☐'} {x}" for x in labels])
        elif "Material Requisition" in p.text and "Job Completion" in p.text:
            labels = ["Material Requisition", "Job Completion"]
            p.text = "   ".join([f"{'☑' if x in selected else '☐'} {x}" for x in labels])

    # Satisfaction is printed in the supplied template; append the chosen level
    # beside the scale without changing the official wording.
    for p in doc.paragraphs:
        if "Dear valued customer" in p.text:
            p.add_run(f"   Selected: {satisfaction}")

    for p in doc.paragraphs:
        if p.text.strip() == "Remarks /Suggestions:":
            p.add_run(f" {remarks}")

    doc.save(output_path)
    return output_path
