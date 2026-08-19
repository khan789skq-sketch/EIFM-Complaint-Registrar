import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def create_ppm_equipment_task_sheet(equipment_list=None):
  """Dynamic Equipment/Task List के साथ Excel Sheet बनाएगा"""
  wb = openpyxl.Workbook()
  ws = wb.active
  ws.title = "PPM Task Sheet"
  ws.views.sheetView[0].showGridLines = True

  # Dynamic Column Widths
  col_widths = {"A": 8, "B": 45, "C": 10, "D": 10, "E": 25, "F": 22}
  for col, width in col_widths.items():
    ws.column_dimensions[col].width = width

  # Borders & Fills
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

  # Fonts
  font_main_header = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
  font_sub_header = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
  font_bold = Font(name="Calibri", size=10, bold=True, color="000000")
  font_regular = Font(name="Calibri", size=10, color="000000")
  font_notice = Font(
      name="Calibri", size=9, bold=True, italic=True, color="C00000"
  )

  # Alignments
  align_center = Alignment(
      horizontal="center", vertical="center", wrap_text=True
  )
  align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

  # Row 1: Company Name
  ws.merge_cells("A1:F1")
  ws["A1"] = "EMIRATES INTERNATIONAL FACILITIES MANAGEMENT"
  ws["A1"].font = font_main_header
  ws["A1"].fill = fill_dark_header
  ws["A1"].alignment = align_center
  ws.row_dimensions[1].height = 28

  # Row 2: Subtitle
  ws.merge_cells("A2:F2")
  ws["A2"] = "PREVENTIVE MAINTENANCE TASK SHEET"
  ws["A2"].font = Font(name="Calibri", size=12, bold=True, color="1F497D")
  ws["A2"].alignment = align_center
  ws.row_dimensions[2].height = 22

  # Metadata Section (Rows 3-8)
  meta_structure = [
      ("Project Name:", "", "Fiscal Year:", "2026"),
      ("Location:", "", "WO Number:", ""),
      ("Unit Number:", "", "Scheduled Month:", ""),
      ("Frequency:", "", "Date of Service:", ""),
      ("Category:", "", "Time Start:", ""),
      ("Equipment Type:", "", "Time Finish:", ""),
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

  # Row 9: Table Headers
  headers = [
      "Sl. No.",
      "Service Specification Task / Equipment Check",
      "OK",
      "Not OK",
      "Remarks",
      "Follow up WO if needed",
  ]
  ws.row_dimensions[9].height = 26
  for c_idx, h_text in enumerate(headers, start=1):
    cell = ws.cell(row=9, column=c_idx, value=h_text)
    cell.font = font_sub_header
    cell.fill = fill_dark_header
    cell.alignment = align_center
    cell.border = border_all_thin

  # Dynamic Checklist Items
  items = equipment_list if equipment_list else [""] * 15
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

  # Notice Row
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
  )
  notice_cell.font = font_notice
  notice_cell.alignment = align_center
  notice_cell.fill = fill_notice
  for col in range(1, 7):
    ws.cell(row=current_row, column=col).border = border_all_thin

  current_row += 1

  # Signature Row
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

  # Maintenance Summary Section
  ws.row_dimensions[current_row].height = 20
  ws.merge_cells(
      start_row=current_row,
      start_column=1,
      end_row=current_row,
      end_column=6,
  )
  sum_cell = ws.cell(
      row=current_row, column=1, value="REPORT SUMMARY OF MAINTENANCE:"
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
  """Default Single Function Call"""
  create_ppm_equipment_task_sheet()


if __name__ == "__main__":
  create_ppm_equipment_task_sheet()

  
