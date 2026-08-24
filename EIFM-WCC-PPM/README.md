# EIFM PPM & WCC Generator

This project is built around the supplied EIFM files:

- `templates/All.xlsx` — original equipment task sheets
- `templates/All-3.xlsx` — original equipment task sheets
- `templates/WCC-08 -EIFMEN08 - Work Completion Certificate.pdf` — supplied WCC front-page reference
- `assets/EIFM_logo.jpg` — extracted from the supplied WCC PDF

## PPM behavior

The PPM number is selected as:

- 1st PPM
- 2nd PPM
- 3rd PPM
- 4th PPM

These are **not four unrelated templates**. They use the same PPM front-page structure; only the selected PPM number changes.

The PPM Details of Work text is:

> Planned Preventive Maintenance Service Complete as per Attached Check List

The generated PPM Excel workbook contains:

1. `PPM Front Page`
2. The selected equipment worksheet copied from the supplied Excel workbook.

The equipment worksheet is retained from the original workbook rather than recreated from scratch.

## WCC behavior

The WCC generator follows the supplied EIFMEN08 Version R3 structure and generates a PDF.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app uses local SQLite for user accounts and records. There is no application-level record-count limit; actual storage is limited by the machine/server storage.

## Important

The original Excel sheets contain their own spelling/wording and formatting. The generator does not rewrite their checklist tasks; it only fills the existing metadata cells and adds the PPM front page.
