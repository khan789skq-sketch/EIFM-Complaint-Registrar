import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import datetime

# ---------------------------------------------------------
# 1. PAGE CONFIG & EIFM BRANDING
# ---------------------------------------------------------
st.set_page_config(page_title="EIFM Document Portal", page_icon="🏢", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #FFFFFF; }
    h1, h2, h3 { color: #0A5C36 !important; font-family: 'Arial', sans-serif; }
    .stButton>button { background-color: #0A5C36; color: white; font-weight: bold; border-radius: 6px; }
    .header-box { background-color: #F0F7F4; padding: 15px; border-left: 6px solid #0A5C36; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. MASTER DATA (BUILDINGS & EQUIPMENTS)
# ---------------------------------------------------------
SITES_LIST = [
    "The Jewels Tower", "Liv Residence", "Prime Business", "Alfa Building", "Al Riffa", 
    "Al Makhool", "Al Ghilani", "Al Findi", "Sobha Daffodil", "Sobha Sapphire", 
    "Sobha Ivory 1", "Sobha Ivory 2", "Al Nahda 1", "Al Nahda 2", "Al Safiya", 
    "Al Barsha", "Square 334", "Red Residence", "Champion Tower", "Frankfurt Tower", 
    "Avenue Residence 2", "Al Qasimiya", "Westbury Residency", "Roya Bank", 
    "Al Mamzar", "Vezul", "11 Villa", "Anantara"
]

EQUIPMENT_LIST = [
    'FCU', 'Split', 'FAHU', 'Plumbing Service', 'Dosing', 'MDB', 'SMDB', 'DB', 
    'ATS', 'VFD', 'Garbage', 'Heater', 'Intercom', 'Ex Fan', 'Str Prss Un', 
    'Capacitor bank', 'GB', 'Transfer Pump', 'Sump', 'Booster Pump', 
    'Chilled water pump', 'Filter pump', 'Chiller', 'Generator', 'SMA', 'Sliding'
]

# Header Title
st.markdown("""
    <div class="header-box">
        <h2 style="margin:0;">EMIRATES INTERNATIONAL FACILITIES MANAGEMENT</h2>
        <p style="margin:0; color:#555;">PPM & Work Completion Document Generator</p>
    </div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. MODE SELECTION
# ---------------------------------------------------------
doc_mode = st.radio("**Select Document Type:**", ["PPM Document (WCC Front Page + Equipment Checklist Below)", "Normal Work Completion Certificate (General WCC)"], horizontal=True)

# ---------------------------------------------------------
# OPTION A: PPM DOCUMENT (WCC FRONT + EXCEL CHECKLIST BELOW)
# ---------------------------------------------------------
if "PPM Document" in doc_mode:
    st.subheader("📋 PPM Integrated Report Generator")
    
    col1, col2 = st.columns(2)
    with col1:
        job_order = st.text_input("Job Order Number", value="3rd PPM Service Year 2026")
        client_name = st.text_input("Client Name", value="Asteco Property Management")
        project_name = st.selectbox("Select Building / Project", SITES_LIST)
        location = st.text_input("Location / Area", value="Main Building / Plant Room")
        tel_no = st.text_input("Tel No.", value="")

    with col2:
        comp_date = st.date_input("Date of Completion", datetime.date.today())
        comp_time = st.time_input("Time of Completion", datetime.time(10, 0))
        selected_equipments = st.multiselect("Select Equipments for Checklist", EQUIPMENT_LIST, default=['FCU', 'Split'])
        site_incharge = st.text_input("Site In-Charge", value="")
        hod_name = st.text_input("HOD Name", value="")

    st.markdown("---")
    st.markdown("### 🛠️ Work Details & Extra Observations")
    work_details = st.text_area("Details of Work", value="Planned Preventive Maintenance Service Completed as per attached Check List.")
    remarks = st.text_area("Remarks / Suggestions (Blank Lines for Print)", value=".......................................................................................................\n.......................................................................................................")

    # Word Generator (Front: WCC, Next: Equipment Checklists)
    def create_ppm_combined_doc():
        doc = Document()
        
        # --- PAGE 1: WCC FRONT PAGE ---
        title = doc.add_heading('WORK COMPLETION CERTIFICATE', level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        t_wcc = doc.add_table(rows=5, cols=2)
        t_wcc.style = 'Table Grid'
        t_wcc.cell(0, 0).text = f"Job Order Number: {job_order}"
        t_wcc.cell(0, 1).text = f"Date & Time: {comp_date} {comp_time}"
        t_wcc.cell(1, 0).text = f"Client: {client_name}"
        t_wcc.cell(1, 1).text = f"Tel No: {tel_no}"
        t_wcc.cell(2, 0).text = f"Project: {project_name}"
        t_wcc.cell(2, 1).text = f"Location: {location}"
        t_wcc.cell(3, 0).text = f"Site In-Charge: {site_incharge}"
        t_wcc.cell(3, 1).text = f"HOD Name: {hod_name}"
        t_wcc.cell(4, 0).merge(t_wcc.cell(4, 1)).text = f"Details of Work:\n{work_details}\n\nRemarks:\n{remarks}"

        doc.add_paragraph("\nClient Signature: ______________________    Date: ____/____/______")
        
        # Footer
        footer = doc.add_paragraph("\nP.O Box 2286, Abu Dhabi – United Arab Emirates - Tel: +971-2-6436663 | E-mail: eifm@eifm.ae")
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # --- PAGE 2 ONWARDS: EQUIPMENT CHECKLISTS BELOW ---
        for eq in selected_equipments:
            doc.add_page_break()
            doc.add_heading(f'PPM CHECKLIST - {eq.upper()}', level=2)
            
            # Equipment Table Structure
            t_eq = doc.add_table(rows=1, cols=3)
            t_eq.style = 'Table Grid'
            hdr = t_eq.rows[0].cells
            hdr[0].text = 'Sl. No.'
            hdr[1].text = 'Maintenance Task / Activity'
            hdr[2].text = 'Status (OK / Not OK / NA)'

            # Fetch tasks from All-3.xlsx if available
            try:
                df = pd.read_excel('All-3.xlsx', sheet_name=eq)
                tasks = df.iloc[8:18, 1].dropna().tolist()
            except:
                tasks = ["Inspect and clean component", "Check electrical terminal wiring", "Check motor noise & vibration", "Check temperature and pressure"]

            for idx, task in enumerate(tasks, 1):
                row = t_eq.add_row().cells
                row[0].text = str(idx)
                row[1].text = str(task)
                row[2].text = "[  ] OK   [  ] Not OK"

        bio = BytesIO()
        doc.save(bio)
        return bio.getvalue()

    st.markdown("---")
    file_data = create_ppm_combined_doc()
    st.download_button(
        label="📥 Download Complete PPM Document (.docx)",
        data=file_data,
        file_name=f"PPM_Report_{project_name}_{comp_date}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# ---------------------------------------------------------
# OPTION B: NORMAL WORK COMPLETION CERTIFICATE (GENERAL WCC)
# ---------------------------------------------------------
else:
    st.subheader("📄 Normal Work Completion Certificate Generator")
    
    col1, col2 = st.columns(2)
    with col1:
        g_job = st.text_input("Job Order Number", value="")
        g_client = st.text_input("Client Name", value="")
        g_project = st.selectbox("Select Building / Project", SITES_LIST)
        g_loc = st.text_input("Location / Unit No.", value="")
        g_tel = st.text_input("Tel No.", value="")

    with col2:
        g_date = st.date_input("Date of Completion", datetime.date.today())
        g_time = st.time_input("Time of Completion", datetime.time(10, 0))
        g_incharge = st.text_input("Site In-Charge", value="")
        g_hod = st.text_input("HOD Name", value="")

    st.markdown("---")
    st.markdown("### 📝 General Work Details (6 Lines / Dotted Lines)")
    line1 = st.text_input("Line 1", value=".........................................................................................................................")
    line2 = st.text_input("Line 2", value=".........................................................................................................................")
    line3 = st.text_input("Line 3", value=".........................................................................................................................")
    line4 = st.text_input("Line 4", value=".........................................................................................................................")
    line5 = st.text_input("Line 5", value=".........................................................................................................................")
    line6 = st.text_input("Line 6", value=".........................................................................................................................")

    def create_normal_wcc():
        doc = Document()
        title = doc.add_heading('WORK COMPLETION CERTIFICATE', level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        t = doc.add_table(rows=4, cols=2)
        t.style = 'Table Grid'
        t.cell(0, 0).text = f"Job Order Number: {g_job}"
        t.cell(0, 1).text = f"Date & Time: {g_date} {g_time}"
        t.cell(1, 0).text = f"Client: {g_client}"
        t.cell(1, 1).text = f"Tel No: {g_tel}"
        t.cell(2, 0).text = f"Project: {g_project}"
        t.cell(2, 1).text = f"Location: {g_loc}"
        t.cell(3, 0).text = f"Site In-Charge: {g_incharge}"
        t.cell(3, 1).text = f"HOD Name: {g_hod}"

        doc.add_paragraph("\nDetails of Work:")
        doc.add_paragraph(f"1. {line1}\n2. {line2}\n3. {line3}\n4. {line4}\n5. {line5}\n6. {line6}")
        
        doc.add_paragraph("\nClient Signature: ______________________    Date: ____/____/______")
        
        footer = doc.add_paragraph("\nP.O Box 2286, Abu Dhabi – United Arab Emirates - Tel: +971-2-6436663 | E-mail: eifm@eifm.ae")
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

        bio = BytesIO()
        doc.save(bio)
        return bio.getvalue()

    st.markdown("---")
    normal_file = create_normal_wcc()
    st.download_button(
        label="📥 Download Normal WCC (.docx)",
        data=normal_file,
        file_name=f"WCC_{g_project}_{g_date}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    
