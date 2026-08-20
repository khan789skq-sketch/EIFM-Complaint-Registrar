from pathlib import Path
import openpyxl
from docx import Document


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"


def _find_template(filename):
    """
    Looks for the template both inside /templates and in the
    repository root. This makes the app work on Streamlit Cloud
    even if the files were uploaded to the root.
    """
    possible_paths = [
        TEMPLATES_DIR / filename,
        BASE_DIR / filename,
    ]

    for path in possible_paths:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Required template file '{filename}' was not found.\n\n"
        f"Please upload it either to:\n"
        f"  {TEMPLATES_DIR / filename}\n"
        f"or:\n"
        f"  {BASE_DIR / filename}"
    )


def _get_excel_templates():
    """
    Returns available Excel template files.
    Missing files are ignored here so importing this module
    does not crash the Streamlit application.
    """
    files = []

    for filename in ("All-3.xlsx", "All.xlsx"):
        possible_paths = [
            TEMPLATES_DIR / filename,
            BASE_DIR / filename,
        ]

        for path in possible_paths:
            if path.exists():
                files.append(path)
                break

    return files


# ============================================================
# EQUIPMENT / SHEET FUNCTIONS
# ============================================================

def _sheet_names(path):
    """Return all worksheet names from an Excel workbook."""
    if not Path(path).exists():
        return []

    wb = openpyxl.load_workbook(
        path,
        read_only=True,
        data_only=False
    )

    names = list(wb.sheetnames)
    wb.close()

    return names


def get_equipment_sheets():
    """
    Returns the union of worksheet names from all available
    supplied Excel templates.
    """
    equipment = []

    for path in _get_excel_templates():
        for sheet in _sheet_names(path):
            if sheet not in equipment:
                equipment.append(sheet)

    return equipment


# Keep this variable for compatibility with the existing app.py.
EQUIPMENT_SHEETS = get_equipment_sheets()


def _source_for_equipment(equipment):
    """
    Find the Excel workbook containing the selected equipment sheet.
    """
    for path in _get_excel_templates():
        if equipment in _sheet_names(path):
            return path

    raise ValueError(
        f"Equipment sheet '{equipment}' was not found in the "
        f"available Excel templates."
    )


# ============================================================
# READ TASKS FROM ORIGINAL TEMPLATE
# ============================================================

def read_template_tasks(equipment):
    """
    Reads checklist tasks from the selected equipment worksheet.
    The original Excel formatting is not changed.
    """
    src = _source_for_equipment(equipment)

    wb = openpyxl.load_workbook(
        src,
        data_only=False
    )

    if equipment not in wb.sheetnames:
        wb.close()
        raise ValueError(
            f"Equipment sheet '{equipment}' does not exist."
        )

    ws = wb[equipment]

    header_row = None

    for row in range(1, ws.max_row + 1):
        value = ws.cell(row, 1).value

        if str(value or "").strip().lower() == "sl. no.":
            header_row = row
            break

    if header_row is None:
        wb.close()
        return []

    tasks = []

    for row in range(header_row + 1, ws.max_row + 1):
        sl_no = ws.cell(row, 1).value
        task = ws.cell(row, 2).value

        if isinstance(sl_no, int) and task:
            tasks.append(str(task))

        elif isinstance(sl_no, float) and sl_no.is_integer() and task:
            tasks.append(str(task))

        elif str(sl_no or "").strip().upper().startswith(
            "GENERAL NOTICE"
        ):
            break

    wb.close()

    return tasks


# ============================================================
# CREATE PPM EXCEL
# ============================================================

def create_ppm_from_template(
    equipment,
    project,
    location,
    unit,
    frequency,
    category,
    fiscal_year,
    wo_number,
    scheduled_month,
    service_date,
    time_start,
    time_finish,
    tasks,
    statuses,
    remarks,
    followups,
    technician,
    engineer,
    summary,
    output_path
):
    """
    Creates the completed PPM Excel using the original supplied
    equipment template as the base.

    Only the selected equipment worksheet is retained.
    Original formatting/layout is preserved.
    """

    src = _source_for_equipment(equipment)

    wb = openpyxl.load_workbook(src)

    if equipment not in wb.sheetnames:
        wb.close()
        raise ValueError(
            f"Equipment sheet not found: {equipment}"
        )

    ws = wb[equipment]

    # --------------------------------------------------------
    # Remove all worksheets except selected equipment
    # --------------------------------------------------------

    for sheet_name in list(wb.sheetnames):
        if sheet_name != equipment:
            del wb[sheet_name]

    # --------------------------------------------------------
    # Header information
    # --------------------------------------------------------

    ws["C3"] = project or ""
    ws["C4"] = location or ""
    ws["C5"] = unit or ""
    ws["C6"] = frequency or ""
    ws["C7"] = category or ""
    ws["C8"] = equipment or ""

    ws["K3"] = fiscal_year or ""
    ws["K4"] = wo_number or ""
    ws["K5"] = scheduled_month or ""
    ws["K6"] = service_date or ""
    ws["K7"] = time_start or ""
    ws["K8"] = time_finish or ""

    # --------------------------------------------------------
    # Find checklist header
    # --------------------------------------------------------

    header_row = None

    for row in range(1, ws.max_row + 1):
        value = ws.cell(row, 1).value

        if str(value or "").strip().lower() == "sl. no.":
            header_row = row
            break

    if header_row is None:
        wb.close()
        raise ValueError(
            "Could not find 'SL. NO.' checklist header "
            "in the selected Excel template."
        )

    # --------------------------------------------------------
    # Find original checklist rows
    # --------------------------------------------------------

    source_rows = []

    for row in range(header_row + 1, ws.max_row + 1):

        sl_no = ws.cell(row, 1).value
        task = ws.cell(row, 2).value

        if isinstance(sl_no, int) and task:
            source_rows.append(row)

        elif (
            isinstance(sl_no, float)
            and sl_no.is_integer()
            and task
        ):
            source_rows.append(row)

        elif str(sl_no or "").strip().upper().startswith(
            "GENERAL NOTICE"
        ):
            break

    # --------------------------------------------------------
    # Safe defaults
    # --------------------------------------------------------

    statuses = statuses or {}
    remarks = remarks or {}
    followups = followups or {}
    tasks = tasks or []

    # --------------------------------------------------------
    # Fill checklist
    # --------------------------------------------------------

    for index, row in enumerate(source_rows, start=1):

        yes_checked = bool(
            statuses.get(index, False)
        )

        no_checked = bool(
            statuses.get(f"no_{index}", False)
        )

        # Status columns
        ws.cell(row, 7).value = "✓" if yes_checked else ""
        ws.cell(row, 8).value = "✓" if no_checked else ""

        # Remarks
        ws.cell(row, 9).value = remarks.get(index, "")

        # Follow-up
        ws.cell(row, 11).value = followups.get(index, "")

        # User-edited task
        if index <= len(tasks):
            if tasks[index - 1]:
                ws.cell(row, 2).value = tasks[index - 1]

    # --------------------------------------------------------
    # Technician / Engineer / Summary
    # --------------------------------------------------------

    for row in range(1, ws.max_row + 1):

        first_cell = str(
            ws.cell(row, 1).value or ""
        ).strip()

        if first_cell.startswith("Tech. Date/Sign:"):
            if technician:
                ws.cell(row, 1).value = (
                    f"Tech. Date/Sign: {technician}"
                )

        elif first_cell.startswith(
            "Eng./Sup Date Sign"
        ):
            if engineer:
                ws.cell(row, 1).value = (
                    f"Eng./Sup Date Sign : {engineer}"
                )

        elif first_cell.startswith("REPORT SUMMARY"):
            if summary and row + 1 <= ws.max_row:
                ws.cell(row + 1, 1).value = summary

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    wb.save(output_path)
    wb.close()

    return str(output_path)


# ============================================================
# WCC DOCUMENT
# ============================================================

def _replace_paragraph_text(paragraph, replacements):
    """
    Replace text in a Word paragraph while keeping the document
    itself as the supplied template.
    """

    original = paragraph.text
    updated = original

    for old, new in replacements:
        if old in updated:
            updated = updated.replace(old, new)

    if updated == original:
        return

    paragraph.text = updated


def create_wcc_from_template(
    job_order,
    client,
    project,
    location,
    tel,
    details,
    completion,
    site_sig,
    site_name,
    site_date,
    site_id,
    hod_sig,
    hod_name,
    hod_date,
    hod_id,
    docs,
    client_sig,
    client_name,
    client_phone,
    satisfaction,
    remarks,
    client_sign_date,
    output_path
):
    """
    Creates WCC from the supplied official Word template.
    """

    src = _find_template(
        "EIFMEN08_WCC_Template.docx"
    )

    doc = Document(src)

    # --------------------------------------------------------
    # Text replacements
    # --------------------------------------------------------

    replacements = [
        (
            "_2nd PPM Service Year 2026____________________",
            f"_{job_order or ''}____________________________"
        ),
        (
            "_East & West International_______________________________",
            f"_{client or ''}_______________________________"
        ),
        (
            "_Marina Gate -2_________________________________________",
            f"_{project or ''}_________________________________________"
        ),
        (
            "Flat - 3206____________________________Tel. No. :- _______",
            f"{location or ''}____________________________Tel. No. :- {tel or ''}"
        ),
        (
            "Date & Time of Completion :- _____________________",
            f"Date & Time of Completion :- {completion or ''}"
        ),
        (
            "Signature of Site in Charge:- ________________Name :-___________ Date :- __________",
            (
                "Signature of Site in Charge:- "
                f"{site_sig or ''}    "
                f"Name :- {site_name or ''}    "
                f"Date :- {site_date or ''}"
            )
        ),
        (
            "8.  Signature of HOD :-\t \t\t\t  Name:- _____________ Date :- _________                           \t\t   ID      :-____________________ ",
            (
                "8.  Signature of HOD :- "
                f"{hod_sig or ''}    "
                f"Name:- {hod_name or ''} "
                f"Date :- {hod_date or ''} "
                f"ID :- {hod_id or ''}"
            )
        ),
        (
            " Client Signature:-  \t\t",
            f" Client Signature:- {client_sig or ''}"
        ),
        (
            "Name: -  \t",
            f"Name: - {client_name or ''}"
        ),
        (
            "Phone No. :-  \t",
            f"Phone No. :- {client_phone or ''}"
        ),
        (
            "Client Signature  ---------------------\tDate :- ____/____/_____",
            (
                "Client Signature  --------------------- "
                f"Date :- {client_sign_date or ''}"
            )
        ),
    ]

    for paragraph in doc.paragraphs:
        _replace_paragraph_text(
            paragraph,
            replacements
        )

    # --------------------------------------------------------
    # Work details
    # --------------------------------------------------------

    detail_lines = [
        line.strip()
        for line in str(details or "").splitlines()
        if line.strip()
    ]

    for index in range(9, 15):

        paragraph_index = index

        if paragraph_index < len(doc.paragraphs):

            value_index = index - 9

            value = (
                detail_lines[value_index]
                if value_index < len(detail_lines)
                else ""
            )

            if value:
                doc.paragraphs[
                    paragraph_index
                ].text = value

    # --------------------------------------------------------
    # Documents
    # --------------------------------------------------------

    selected = set(docs or [])

    for paragraph in doc.paragraphs:

        text = paragraph.text

        if (
            "LPO" in text
            and "Invoice" in text
        ):

            labels = [
                "LPO",
                "Invoice",
                "Delivery Note",
                "Petty Cash",
            ]

            paragraph.text = "   ".join(
                [
                    (
                        f"{'☑' if label in selected else '☐'} "
                        f"{label}"
                    )
                    for label in labels
                ]
            )

        elif (
            "Material Requisition" in text
            and "Job Completion" in text
        ):

            labels = [
                "Material Requisition",
                "Job Completion",
            ]

            paragraph.text = "   ".join(
                [
                    (
                        f"{'☑' if label in selected else '☐'} "
                        f"{label}"
                    )
                    for label in labels
                ]
            )

    # --------------------------------------------------------
    # Customer satisfaction
    # --------------------------------------------------------

    for paragraph in doc.paragraphs:

        if "Dear valued customer" in paragraph.text:

            if satisfaction:
                paragraph.add_run(
                    f"   Selected: {satisfaction}"
                )

    # --------------------------------------------------------
    # Remarks
    # --------------------------------------------------------

    for paragraph in doc.paragraphs:

        if paragraph.text.strip() == "Remarks /Suggestions:":

            if remarks:
                paragraph.add_run(
                    f" {remarks}"
                )

    # --------------------------------------------------------
    # Save WCC
    # --------------------------------------------------------

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    doc.save(output_path)

    return str(output_path)
