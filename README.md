# EIFM WCC & PPM — Streamlit

Complete EIFM PPM & WCC generator using the supplied Excel equipment checklists and EIFMEN08 WCC template.

## Included
- `All.xlsx` and `All-3.xlsx` — original equipment checklist workbooks.
- `08 -EIFMEN08 - Work Completion Certificate.docx` — WCC template.
- `WCC-08 -EIFMEN08 - Work Completion Certificate.pdf` — supplied normal/blank WCC reference.
- `EIFM_logo.jpg` — supplied logo.

## Final behavior
- Normal WCC: no PPM wording; Before + After photos are cropped/resized and placed together on one page.
- Normal WCC signatures use finger/stylus signature pads, not typed signature text.
- PPM WCC: PPM front page plus ONE Excel checklist workbook containing any number of selected equipment sheets.
- Multiple equipment can be selected at once (1, 3, 4, 5, 60+ as available); only selected equipment details/checklists are included.
- Building-specific Excel checklist files can be saved in the Checklist Library and selected later.
- Generated records are stored under `outputs/`; each generation also creates one ZIP package.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```
