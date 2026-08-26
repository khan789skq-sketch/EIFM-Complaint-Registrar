
# EIFM WCC & PPM — Streamlit

This project is built around the supplied source files:

- `templates/All.xlsx`
- `templates/All-3.xlsx`
- `templates/EIFMEN08_WCC_Template.docx`
- `assets/EIFM_logo.jpg`

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## What it does

- Sign in / sign up with a local SQLite account.
- New PPM:
  - selects from the equipment worksheet names found in BOTH supplied Excel files;
  - loads the original checklist text from that equipment worksheet;
  - lets the user enter project/location/unit/frequency/category/year/WO/month/date/time;
  - lets the user mark OK / Not OK, remarks and follow-up WO;
  - copies the selected original worksheet and fills the supplied cells without rebuilding the sheet design.
- New WCC:
  - uses the supplied EIFMEN08 Version R3 Word file as the base;
  - fills the WCC information while retaining the supplied logo/footer/template.
- My Records stores generated file names in SQLite.

## Important

The PPM generator intentionally uses the supplied workbook as a template rather than creating a new blue table.

The WCC generator intentionally starts from the supplied Word document rather than creating a new WCC design.

For a production deployment, use an external database/object storage if records must survive server restarts/redeployments.
