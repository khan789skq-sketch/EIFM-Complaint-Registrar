import os
import generate_sheet
import streamlit as st

st.set_page_config(
    page_title="EIFM Maintenance & WCC Generator", page_icon="🏢", layout="wide"
)

st.title("🏢 EIFM Maintenance & WCC Task Sheet Generator")

# Sidebar Configurations
st.sidebar.header("⚙️ Sheet & Site Setup")

site_title = st.sidebar.text_input(
    "Company / Header Name", "EMIRATES INTERNATIONAL FACILITIES MANAGEMENT"
)

doc_type = st.sidebar.radio(
    "Select Sheet Type",
    ["PPM Task Sheet", "WCC / Complaint Sheet"],
)

st.sidebar.subheader("🏢 Site & Unit Details")
building_name = st.sidebar.text_input("Building / Site Name", "Sharjah Tower A")
location = st.sidebar.text_input("Location / Zone", "Mechanical Room - B1")
unit_no = st.sidebar.text_input("Unit / Apartment No.", "Unit 402")

st.sidebar.subheader("🛠️ System & Equipment")
category = st.sidebar.selectbox(
    "Category", ["HVAC / AC System", "Electrical", "Plumbing", "Fire Fighting"]
)
eq_type = st.sidebar.text_input("Equipment Type / Tag", "FCU-01 (Fan Coil Unit)")

st.sidebar.subheader("📋 Service & Work Order Details")
ppm_type = st.sidebar.selectbox(
    "PPM Frequency",
    [
        "PPM 1 (Monthly)",
        "PPM 2 (Quarterly)",
        "PPM 3 (Semi-Annual)",
        "PPM 4 (Annual)",
        "Ad-hoc / Corrective",
    ],
)
wo_number = st.sidebar.text_input("WO / WCC Number", "WO-2026-8801")
scheduled_month = st.sidebar.selectbox(
    "Scheduled Month",
    [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
)
service_date = st.sidebar.text_input("Date of Service", "19/08/2026")

# Tasks Input Section
st.subheader("📝 Customize Checklist Items / Maintenance Tasks")
default_tasks = (
    "Check FCU Filters and Clean\n"
    "Inspect Thermostat and Blower Fan\n"
    "Check Electrical Connections & Ampere\n"
    "Clean Condensate Drain Tray\n"
    "Check Motor Bearings and Lubrication\n"
    "Inspect Actuator Valve Operation"
)
tasks_input = st.text_area(
    "Type tasks here (One task per line):", value=default_tasks, height=180
)
task_list = [t.strip() for t in tasks_input.split("\n") if t.strip()]

# Metadata Payload
meta_payload = {
    "site_title": site_title,
    "doc_type": doc_type,
    "building": building_name,
    "location": location,
    "unit_no": unit_no,
    "category": category,
    "eq_type": eq_type,
    "ppm_type": ppm_type,
    "wo_number": wo_number,
    "month": scheduled_month,
    "service_date": service_date,
}

# Generate Excel File
try:
  file_path = generate_sheet.create_ppm_equipment_task_sheet(
      task_list, meta_payload
  )

  st.success("✅ Excel Sheet Generated Successfully!")
  st.markdown("---")

  # Download Button
  if os.path.exists("PPM_Equipment_Task_Sheet.xlsx"):
    with open("PPM_Equipment_Task_Sheet.xlsx", "rb") as file:
      st.download_button(
          label="📥 Download Excel Sheet (.xlsx)",
          data=file,
          file_name=(
              f"{doc_type.replace(' ', '_')}_{building_name.replace(' ', '_')}.xlsx"
          ),
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
      )
except Exception as err:
  st.error(f"Error generating file: {err}")
  
