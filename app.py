import generate_sheet
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="EIFM PPM Task Sheet Generator", page_icon="📊", layout="wide"
)

st.title("📋 EIFM Preventive Maintenance Task Sheet Manager")

# Default Equipment Checklists
default_tasks = [
    "Check FCU Filters and Clean",
    "Inspect Thermostat and Blower Fan",
    "Check Electrical Connections & Ampere",
    "Clean Condensate Drain Tray",
    "Check Motor Bearings and Lubrication",
]

# Sidebar Configuration
st.sidebar.header("⚙️ PPM Configuration")
selected_category = st.sidebar.selectbox(
    "Select System Category",
    ["HVAC / AC System", "Electrical", "Plumbing", "Fire Fighting"],
)

# Generate Excel File
generate_sheet.create_ppm_equipment_task_sheet(default_tasks)

st.subheader("📄 Excel Preview")

# Display Table Preview
try:
  df = pd.read_excel("PPM_Equipment_Task_Sheet.xlsx")
  st.dataframe(df, use_container_width=True)
except Exception as e:
  st.success("Excel sheet generated successfully!")

st.markdown("---")

# Download Button
with open("PPM_Equipment_Task_Sheet.xlsx", "rb") as file:
  st.download_button(
      label="📥 Download Blank PPM Equipment Excel Sheet (.xlsx)",
      data=file,
      file_name="PPM_Equipment_Task_Sheet.xlsx",
      mime=(
          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
      ),
  )
  
