import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def create_ppm_equipment_task_sheet(*args, **kwargs):
  equipment_list = args[0] if len(args) > 0 else kwargs.get("equipment_list", [])
  meta = args[1] if len(args) > 1 else kwargs.get("meta", {})

  if not isinstance(meta, dict):
    meta = {}

  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "PPM & WCC Task Sheet"
  ws.views.sheetView[0].showGridLines = True

  col_widths = {"A": 8, "B": 45, "C": 10, "D": 10, "E": 25, "F": 22}
  for col, width in col_widths.items():
    ws.column_dimensions[col].width = width

  thin = Side(border_style="thin", color="000000")
  border_all_thin = Border(left=thin, right=thin, top=thin, bottom=thin)

  fill_dark_header = PatternFill(
      start_color="1F497D", end_color="1F497D", fill_type="solid"
  )
  fill_sub_header = PatternFill(
      start_color="DCE6F1", end_color="DCE6F1", fill_type="solid"
  )
  fill_notice = PatternFill(
      start_color="F2DCDB", end_color="F2DCDB", fill_type="solid"
  )

  font_main_header = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
  font_sub_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
  font_bold = Font(name="Calibri", size=10, bold=True, color="000000")
  font_regular = Font(name="Calibri", size=10, color="000000")
  font_notice = Font(
      name="Calibri", size=9, bold=True, italic=True, color="C00000"
  )

  align_center = Alignment(
      horizontal="center", vertical="center", wrap_text=True
  )
  align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

  # Title Header
  ws.merge_cells("A1:F1")
  ws["A1"] = (
      meta.get("site_title", "EMIRATES INTERNATIONAL FACILITIES MANAGEMENT")
      .strip()
      .upper()
  )
  ws["A1"].font = font_main_header
  ws["A1"].fill = fill_dark_header
  ws["A1"].alignment = align_center
  ws.row_dimensions[1].height = 28

  # Sub Title
  ws.merge_cells("A2:F2")
  sheet_mode = meta.get("doc_type", "PPM TASK SHEET")
  ppm_freq = meta.get("ppm_type", "")
  sub_title_text = (
      f"WORK COMPLETION CERTIFICATE (WCC) & {sheet_mode}"
      if "WCC" in sheet_mode
      else f"PREVENTIVE MAINTENANCE TASK SHEET ({ppm_freq})"
  )
  ws["A2"] = sub_title_text
  ws["A2"].font = Font(name="Calibri", size=12, bold=True, color="1F497D")
  ws["A2"].alignment = align_center
  ws.row_dimensions[2].height = 22

  # Metadata
  meta_structure = [
      (
          "Site / Building Name:",
          meta.get("building", ""),
          "Fiscal Year:",
          "2026",
      ),
      (
          "Location / Zone:",
          meta.get("location", ""),
          "WO / WCC No:",
          meta.get("wo_number", ""),
      ),
      (
          "Unit / Flat No:",
          meta.get("unit_no", ""),
          "Scheduled Month:",
          meta.get("month", ""),
      ),
      (
          "Service / PPM Type:",
          meta.get("ppm_type", ""),
          "Date of Service:",
          meta.get("service_date", ""),
      ),
      ("Category / System:", meta.get("category", ""), "Time Start:", ""),
      ("Equipment Model / Type:", meta.get("eq_type", ""), "Time Finish:", ""),
  ]

  for r_idx, row_data in enumerate(meta_structure, start=3):
    ws.row_dimensions[r_idx].height = 20
    ws.cell(row=r_idx, column=1, value=row_data[0]).font = font_bold
    ws.cell(row=r_idx, column=1).alignment = align_left
    ws.cell(row=r_idx, column=1).fill = fill_sub_header

    ws.merge_cells(start_row=r_idx, start_column=2, end_row=r_idx, end_column=3)
    ws.cell(row=r_idx, column=2, value=row_data[1]).font = font_regular

    ws.cell(row=r_idx, column=4, value=row_data[2]).font = font_bold
    ws.cell(row=r_idx, column=4).alignment = align_left
    ws.cell(row=r_idx, column=4).fill = fill_sub_header

    ws.merge_cells(start_row=r_idx, start_column=5, end_row=r_idx, end_column=6)
    ws.cell(row=r_idx, column=5, value=row_data[3]).font = font_regular

    for col in range(1, 7):
      ws.cell(row=r_idx, column=col).border = border_all_thin

  # Headers Row
  headers = [
      "Sl. No.",
      "Service Specification Task / Equipment Check",
      "OK",
      "Not OK",
      "Remarks",
      "Follow up WO / WCC Needed",
  ]
  ws.row_dimensions[9].height = 26
  for c_idx, h_text in enumerate(headers, start=1):
    cell = ws.cell(row=9, column=c_idx, value=h_text)
    cell.font = font_sub_header
    cell.fill = fill_dark_header
    cell.alignment = align_center
    cell.border = border_all_thin

  # Tasks
  items = equipment_list if equipment_list else [""] * 12
  current_row = 10

  for idx, task_name in enumerate(items, start=1):
    ws.row_dimensions[current_row].height = 22
    ws.cell(row=current_row, column=1, value=idx).alignment = align_center
    ws.cell(row=current_row, column=1).font = font_regular

    ws.cell(row=current_row, column=2, value=task_name).alignment = align_left
    ws.cell(row=current_row, column=2).font = font_regular

    for col in range(1, 7):
      ws.cell(row=current_row, column=col).border = border_all_thin
    current_row += 1

  # Notice
  ws.merge_cells(
      start_row=current_row,
      start_column=1,
      end_row=current_row,
      end_column=6,
  )
  ws.row_dimensions[current_row].height = 32
  notice_cell = ws.cell(row=current_row, column=1)
  notice_cell.value = (
      "GENERAL NOTICE: Appropriate PPE is to be worn at all times ensuring"
      " works are carried out in pairs where access is limited and/or at height."
      " All works will be scheduled in advance and the occupier/tenant must be"
      " informed prior to the service."
  )
  notice_cell.font = font_notice
  notice_cell.alignment = align_center
  notice_cell.fill = fill_notice
  for col in range(1, 7):
    ws.cell(row=current_row, column=col).border = border_all_thin

  current_row += 1

  # Signatures
  ws.row_dimensions[current_row].height = 24
  ws.merge_cells(
      start_row=current_row,
      start_column=1,
      end_row=current_row,
      end_column=3,
  )
  ws.merge_cells(
      start_row=current_row,
      start_column=4,
      end_row=current_row,
      end_column=6,
  )
  ws.cell(
      row=current_row, column=1, value="Tech. Date/Sign: _______________________"
  ).font = font_bold
  ws.cell(
      row=current_row,
      column=4,
      value="Eng./Sup Date Sign: _______________________",
  ).font = font_bold
  for col in range(1, 7):
    ws.cell(row=current_row, column=col).border = border_all_thin

  current_row += 1

  # Report / WCC Summary
  ws.row_dimensions[current_row].height = 20
  ws.merge_cells(
      start_row=current_row,
      start_column=1,
      end_row=current_row,
      end_column=6,
  )
  sum_cell = ws.cell(
      row=current_row,
      column=1,
      value="REPORT SUMMARY OF MAINTENANCE / WCC COMPLAINT WORK:",
  )
  sum_cell.font = font_bold
  sum_cell.fill = fill_sub_header
  for col in range(1, 7):
    ws.cell(row=current_row, column=col).border = border_all_thin

  for _ in range(4):
    current_row += 1
    ws.row_dimensions[current_row].height = 20
    ws.merge_cells(
        start_row=current_row,
        start_column=1,
        end_row=current_row,
        end_column=6,
    )
    for col in range(1, 7):
      ws.cell(row=current_row, column=col).border = border_all_thin

  wb.save("PPM_Equipment_Task_Sheet.xlsx")


def create_preventive_maintenance_sheet():
  create_ppm_equipment_task_sheet()
    
