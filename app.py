import os
import generate_sheet
import streamlit as st

st.set_page_config(
    page_title="EIFM PPM & WCC Task Sheet Generator",
    page_icon="📋",
    layout="wide",
)

st.title("📋 EIFM PPM & WCC Generator")

st.markdown("---")

# 1. Main Document & Site Settings (No Collapsed Sidebar)
st.subheader("🏢 Site & Client Details")
col1, col2 = st.columns(2)

with col1:
  site_title = st.text_input(
      "Company Name / Header", "EMIRATES INTERNATIONAL FACILITIES MANAGEMENT"
  )
  client_name = st.text_input("Client / Customer Name", "Client Name Ltd")
  building_name = st.text_input("Site / Building Name", "Sharjah Project")
  unit_no = st.text_input("Unit / Area No.", "Unit 101")

with col2:
  doc_type = st.radio(
      "Select Sheet Type",
      ["PPM Task Sheet", "WCC / Complaint Sheet"],
      horizontal=True,
  )
  location = st.text_input("Location / Zone", "Plant Room - B1")
  category = st.selectbox(
      "Category",
      ["HVAC / AC System", "Electrical", "Plumbing", "Fire Fighting"],
  )
  eq_type = st.text_input("Equipment Type / Tag", "FCU (Fan Coil Unit)")

st.markdown("---")

# 2. Service & WO Details
st.subheader("📑 Service & Work Order Details")
col3, col4 = st.columns(2)

with col3:
  ppm_type = st.selectbox(
      "PPM Frequency",
      [
          "PPM 1 (Monthly)",
          "PPM 2 (Quarterly)",
          "PPM 3 (Semi-Annual)",
          "PPM 4 (Annual)",
          "Corrective / Complaint",
      ],
  )
  wo_number = st.text_input("WO / WCC Number", "WO-2026-001")

with col4:
  scheduled_month = st.selectbox(
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
  service_date = st.text_input("Date of Service", "19/08/2026")

st.markdown("---")

# 3. Tasks Input Section
st.subheader("📝 Maintenance Checklist Items")
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
    "client_name": client_name,
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
    
