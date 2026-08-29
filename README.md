# EIFM WCC & PPM — Streamlit

## GitHub upload
Upload **all files in this folder directly into the repository root**. No `templates` folder is required.

Required root files:
- `app.py`
- `generate_sheet.py`
- `requirements.txt`
- `All.xlsx`
- `All-3.xlsx`
- `08 -EIFMEN08 - Work Completion Certificate.docx`
- `EIFM_logo.jpg`

## Run
`streamlit run app.py`

The app reads the supplied Excel workbooks directly, preserves the selected original equipment worksheet, and uses the supplied EIFMEN08 Word document as the WCC base template.
