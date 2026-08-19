import generate_sheet
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="EIFM PPM & Complaint Task Sheet", page_icon="📋", layout="wide"
)

st.title("📋 EIFM Preventive Maintenance & WCC Task Sheet Manager")

# Sidebar Configuration
st.sidebar.header("⚙️ Sheet Configuration")

# Building & Location Details
st.sidebar.subheader("🏢 Building Details")
building_name = st.sidebar.text_input("Building Name", "Main Tower A")
location = st.sidebar.text_input("Location / Zone", "Mechanical Room - Basement")
unit_no = st.sidebar.text_input("Unit / Area No.", "A-102")

# Category & Equipment List
st.sidebar.subheader("🛠️ System & Equipment")
category = st.sidebar.selectbox(
    "Category", ["HVAC / AC System", "Electrical", "Plumbing", "Fire Fighting"]
)
eq_type = st.sidebar.selectbox(
    "Equipment Type",
    [
        "FCU (Fan Coil Unit)",
        "AHU (Air Handling Unit)",
        "FAHU",
        "Chiller",
        "Water Pump",
        "Main Distribution Board (MDB)",
    ],
)

# PPM Type Selection (PPM 1, 2, 3, 4)
st.sidebar.subheader("📅 PPM & WCC Type")
ppm_type = st.sidebar.selectbox(
    "Select PPM Frequency",
    ["PPM 1 (Monthly)", "PPM 2 (Quarterly)", "PPM 3 (Semi-Annual)", "PPM 4 (Annual)"],
)
wo_number = st.sidebar.text_input("WO / WCC Number", "WO-2026-0012")
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

# Dynamic Tasks Input (Custom Equipment List)
st.subheader("📝 Maintenance Checklist Items")
default_tasks_text = (
    "Check FCU Filters and Clean\nInspect Thermostat and Blower Fan\nCheck"
    " Electrical Connections & Ampere\nClean Condensate Drain Tray\nCheck Motor"
    " Bearings and Lubrication"
)
tasks_input = st.text_area(
    "Enter Tasks (One per line):", value=default_tasks_text, height=150
)
task_list = [t.strip() for t in tasks_input.split("\n") if t.strip()]

# Generate Sheet Trigger
metadata = {
    "building": building_name,
    "location": location,
    "unit_no": unit_no,
    "category": category,
    "eq_type": eq_type,
    "ppm_type": ppm_type,
    "wo_number": wo_number,
    "month": scheduled_month,
}

generate_sheet.create_ppm_equipment_task_sheet(task_list, metadata)

st.markdown("---")
st.subheader("📄 Dynamic Excel Sheet Preview")

try:
  df = pd.read_excel("PPM_Equipment_Task_Sheet.xlsx")
  st.dataframe(df, use_container_width=True)
except Exception as e:
  st.info("Excel Sheet Ready.")

st.markdown("---")

# Download Button
with open("PPM_Equipment_Task_Sheet.xlsx", "rb") as file:
  st.download_button(
      label="📥 Download Generated Excel Sheet (.xlsx)",
      data=file,
      file_name=f"PPM_Sheet_{building_name}_{ppm_type.replace(' ', '_')}.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
    
