import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
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

# Standard tasks mapped for all equipment types if excel sheet isn't loaded
DEFAULT_EQUIPMENT_TASKS = {
    'FCU': [
        "Condition of Blower and Cooling Coil",
        "Check condition of Motor for abnormal noise/vibration",
        "Check and clean evaporator drain pan",
        "Check electrical wiring connection, tight if required",
        "Check the function of actuator, proper closing and opening",
        "Clean drain with compressed air or nitrogen",
        "Check for Joint/Pipe Leak or insulation leaks",
        "Check and service Air Filter",
        "Servicing of complete system",
        "Check thermostat and valve operation status"
    ],
    'Split': [
        "Clean indoor unit air filters and evaporator coil",
        "Check outdoor unit condenser coil and clean",
        "Check refrigerant pressure and gas leaks",
        "Inspect electrical terminals and connections",
        "Check compressor operating current/amperage",
        "Clean condensate drain line and tray"
    ],
    'FAHU': [
        "Inspect supply/exhaust fan motors and belts",
        "Check heat recovery wheel / heat exchanger condition",
        "Inspect pre-filters, bag filters and replace if needed",
        "Check chilled water valves and actuators",
        "Inspect electrical control panel and VFD operation"
    ]
}

# Generic fallback tasks for remaining equipments
GENERIC_TASKS = [
    "Visual inspection of equipment condition and mounting",
    "Check all electrical connections and terminal tightness",
    "Clean equipment body, filters, and surroundings",
    "Check for abnormal noise, vibration, or overheating",
    "Inspect valves, pipe joints, and pressure gauges",
    "Verify operational sequence and control settings",
    "Test safety trips and emergency shutdown controls",
    "Record voltage, current, and operating pressure",
    "Apply lubrication to bearings/moving parts where required",
    "Final functional testing and system sign-off"
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
doc_mode = st.radio("**Select Document Type:**", ["PPM Document (WCC Front Page + Exact Task Sheet Below)", "Normal Work Completion Certificate (General WCC)"], horizontal=True)

# ---------------------------------------------------------
# OPTION A: PPM DOCUMENT WITH EXACT TASK SHEET MATCHING IMAGE
# ---------------------------------------------------------
if "PPM Document" in doc_mode:
    st.subheader("📋 PPM Integrated Report Generator")
    
    col1, col2 = st.columns(2)
    with col1:
        job_order = st.text_input("Job Order / WO Number", value="WO-2026-001")
        client_name = st.text_input("Client Name", value="Asteco Property Management")
        project_name = st.selectbox("Select Building / Project", SITES_LIST)
        location = st.text_input("Location / Area", value="Main Building / Plant Room")
        unit_no = st.text_input("Unit Number", value="Common Area")
        tel_no = st.text_input("Tel No.", value="")

    with col2:
        comp_date = st.date_input("Date of Service", datetime.date.today())
        frequency = st.selectbox("Frequency", ["Monthly", "Quarterly", "Semi-Annual", "Annual"], index=1)
        category_type = st.selectbox("Category", ["HVAC", "Electrical", "Plumbing", "Civil", "Specialist"], index=0)
        selected_equipments = st.multiselect("Select Equipments for Checklist", EQUIPMENT_LIST, default=['FCU', 'Split'])
        site_incharge = st.text_input("Site In-Charge", value="")
        hod_name = st.text_input("HOD Name", value="")

    st.markdown("---")
    st.markdown("### 🛠️ Work Details & Extra Observations")
    work_details = st.text_area("Details of Work", value="Planned Preventive Maintenance Service Completed as per attached Check List.")
    remarks = st.text_area("Remarks / Suggestions (Blank Lines for Print)", value=".......................................................................................................\n.......................................................................................................")

    def create_ppm_combined_doc():
        doc = Document()
        
        # --- PAGE 1: WCC FRONT PAGE ---
        title = doc.add_heading('WORK COMPLETION CERTIFICATE', level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        t_wcc = doc.add_table(rows=5, cols=2)
        t_wcc.style = 'Table Grid'
        t_wcc.cell(0, 0).text = f"Job Order Number: {job_order}"
        t_wcc.cell(0, 1).text = f"Date: {comp_date}"
        t_wcc.cell(1, 0).text = f"Client: {client_name}"
        t_wcc.cell(1, 1).text = f"Tel No: {tel_no}"
        t_wcc.cell(2, 0).text = f"Project: {project_name}"
        t_wcc.cell(2, 1).text = f"Location: {location}"
        t_wcc.cell(3, 0).text = f"Site In-Charge: {site_incharge}"
        t_wcc.cell(3, 1).text = f"HOD Name: {hod_name}"
        t_wcc.cell(4, 0).merge(t_wcc.cell(4, 1)).text = f"Details of Work:\n{work_details}\n\nRemarks:\n{remarks}"

        doc.add_paragraph("\nClient Signature: ______________________    Date: ____/____/______")
        
        footer = doc.add_paragraph("\nP.O Box 2286, Abu Dhabi – United Arab Emirates - Tel: +971-2-6436663 | E-mail: eifm@eifm.ae")
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # --- PAGE 2 ONWARDS: EXACT PREVENTIVE MAINTENANCE TASK SHEET FOR EACH SELECTED EQUIPMENT ---
        for eq in selected_equipments:
            doc.add_page_break()
            
            # Title
            h = doc.add_heading('Preventive Maintenance Task Sheet', level=1)
            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # 1. Metadata Box (Same structure as Excel image)
            t_meta = doc.add_table(rows=6, cols=4)
            t_meta.style = 'Table Grid'
            
            t_meta.cell(0, 0).text = "Project Name"
            t_meta.cell(0, 1).text = str(project_name)
            t_meta.cell(0, 2).text = "Fiscal Year"
            t_meta.cell(0, 3).text = str(comp_date.year)
            
            t_meta.cell(1, 0).text = "Location"
            t_meta.cell(1, 1).text = str(location)
            t_meta.cell(1, 2).text = "WO Number"
            t_meta.cell(1, 3).text = str(job_order)
            
            t_meta.cell(2, 0).text = "Unit Number"
            t_meta.cell(2, 1).text = str(unit_no)
            t_meta.cell(2, 2).text = "Scheduled Month"
            t_meta.cell(2, 3).text = comp_date.strftime("%B")
            
            t_meta.cell(3, 0).text = "Frequency"
            t_meta.cell(3, 1).text = str(frequency)
            t_meta.cell(3, 2).text = "Date of Service"
            t_meta.cell(3, 3).text = str(comp_date)
            
            t_meta.cell(4, 0).text = "Category"
            t_meta.cell(4, 1).text = str(category_type)
            t_meta.cell(4, 2).text = "Time Start"
            t_meta.cell(4, 3).text = "________"
            
            t_meta.cell(5, 0).text = "Equipment Type"
            t_meta.cell(5, 1).text = str(eq)
            t_meta.cell(5, 2).text = "Time Finish"
            t_meta.cell(5, 3).text = "________"

            doc.add_paragraph("") # Space

            # 2. Main Tasks Table (Columns: Sl. No | Service Specification Task | OK | Not OK | Remarks | Follow up W.O.)
            t_task = doc.add_table(rows=1, cols=6)
            t_task.style = 'Table Grid'
            hdr = t_task.rows[0].cells
            hdr[0].text = 'Sl. No.'
            hdr[1].text = 'Service Specification Task'
            hdr[2].text = 'OK'
            hdr[3].text = 'Not OK'
            hdr[4].text = 'Remarks'
            hdr[5].text = 'Follow up W.O. if needed'

            # Try Excel sheet first, fallback to mapped/generic tasks
            tasks = []
            try:
                df = pd.read_excel('All-3.xlsx', sheet_name=eq)
                tasks = df.iloc[8:19, 1].dropna().tolist()
            except:
                pass
            
            if not tasks:
                tasks = DEFAULT_EQUIPMENT_TASKS.get(eq, GENERIC_TASKS)

            for idx, task in enumerate(tasks, 1):
                row = t_task.add_row().cells
                row[0].text = str(idx)
                row[1].text = str(task)
                row[2].text = "[  ]"
                row[3].text = "[  ]"
                row[4].text = ""
                row[5].text = ""

            # 3. General Notice
            doc.add_paragraph("")
            notice_p = doc.add_paragraph()
            r = notice_p.add_run("GENERAL NOTICE: Appropriate PPE is to be worn at all times ensuring works are carried out in pairs where access is limited and/or at height. All works will be scheduled in advance and the occupier/tenant must be informed prior to the service.")
            r.font.size = Pt(8)
            r.font.italic = True
            r.font.color.rgb = RGBColor(200, 0, 0)

            # 4. Signatures & Report Summary Box (Matching Image Bottom)
            t_sign = doc.add_table(rows=2, cols=2)
            t_sign.style = 'Table Grid'
            t_sign.cell(0, 0).text = "Tech. Date/Sign:"
            t_sign.cell(0, 1).text = "Eng./Sup Date Sign:"
            t_sign.cell(1, 0).merge(t_sign.cell(1, 1)).text = "REPORT SUMMARY OF MAINTENANCE:\n\n\n\n"

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
        
