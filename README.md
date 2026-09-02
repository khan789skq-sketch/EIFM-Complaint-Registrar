# EIFM WCC & PPM Generator

Streamlit app for EIFM PPM and WCC generation.

## Included functionality
- PPM generated from the supplied `All.xlsx` / `All-3.xlsx` equipment worksheets without rebuilding their checklist layout.
- Equipment-specific details/checklists for FCU, DB, SMDB and every supplied equipment sheet.
- 1st, 2nd, 3rd and 4th PPM selection.
- Building Checklist Library: save different Excel checklist workbooks for different buildings. A workbook may contain any number of sheets/pages.
- Normal WCC: no PPM wording; requires Before Picture and After Picture and inserts both into the WCC document.
- PPM WCC: uses the supplied EIFMEN08 WCC front page and attaches the selected building Excel checklist.
- Login and My Records.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
