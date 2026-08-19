import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="EIFM Portal & Operations", page_icon="🏢", layout="wide")

# Header & Logo Section
st.title("🏢 Emirates International Facilities Management (EIFM)")
st.subheader("Integrated FM Operations, Complaint & PPM Management Portal")
st.write("---")

# Navigation Tabs
tab1, tab2, tab3 = st.tabs(["📋 Complaint & Work Order", "📄 WCC (Work Completion Certificate)", "🛠️ PPM Schedules & Equipment"])

# --- TAB 1: COMPLAINT REGISTRATION ---
with tab1:
    st.header("Register Facility Complaint / Job Request")
    
    with st.form("complaint_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            building = st.selectbox("Building / Facility Name*", [
                "Select Building...",
                "Sharjah Sites / Residential Towers",
                "EIFM Main Office / Facility Center",
                "Commercial Units & Plaza",
                "Other Dedicated Site"
            ])
            flat_no = st.text_input("Flat / Office / Area Location*")
            reported_by = st.text_input("Reported By (Name)*")
            
        with col2:
            req_date = st.date_input("Date", datetime.today())
            contact = st.text_input("Contact Number / Ext")
            priority = st.selectbox("Priority Level", ["Low", "Medium", "High", "Emergency / Critical"])

        category = st.selectbox("Service Category*", [
            "HVAC / Air Conditioning (Chillers, FCU, AHU)",
            "Electrical Systems & Panels",
            "Plumbing & Drainage",
            "Civil, Carpentry & Painting",
            "Cleaning & Janitorial Services",
            "Pest Control & Waste Management"
        ])
        
        details = st.text_area("Detailed Issue Description*")
        
        btn_complaint = st.form_submit_button("Submit Work Request")
        if btn_complaint:
            if building != "Select Building..." and reported_by and details:
                st.success(f"✅ Complaint Registered Successfully for {building} ({flat_no})")
            else:
                st.error("⚠️ Please fill in all required fields marked with *")

# --- TAB 2: WORK COMPLETION CERTIFICATE (WCC) ---
with tab2:
    st.header("📄 Work Completion Certificate (WCC) Front Page")
    
    with st.form("wcc_form"):
        c1, c2 = st.columns(2)
        with c1:
            wcc_no = st.text_input("WCC Number", "WCC-EIFM-2026-001")
            client_name = st.text_input("Client / Building Management Name")
            site_loc = st.text_input("Site Location / Sharjah Branch")
        with c2:
            comp_date = st.date_input("Completion Date", datetime.today())
            supervisor = st.text_input("EIFM Supervisor / Engineer In-Charge")
            contract_ref = st.text_input("Contract Ref / LPO No.")
            
        st.subheader("Scope of Work Completed")
        work_done = st.text_area("Summary of Completed Maintenance / Civil Work")
        
        client_sign = st.checkbox("Client Approval / Sign-off Confirmed")
        
        btn_wcc = st.form_submit_button("Generate WCC Record")
        if btn_wcc:
            st.success(f"📄 WCC {wcc_no} Generated Successfully!")

# --- TAB 3: PPM SCHEDULES & EQUIPMENT LIST ---
with tab3:
    st.header("🛠️ Planned Preventive Maintenance (PPM) & Asset Tracker")
    
    st.subheader("1. Equipment Asset List")
    equipment_data = {
        "Asset ID": ["EQ-HVAC-01", "EQ-ELEC-02", "EQ-PLUMB-03", "EQ-FIRE-04"],
        "Equipment Name": ["AHU / FCU Units", "Main Distribution Board (MDB)", "Water Transfer Pumps", "Fire Alarm Panel"],
        "Location": ["Sharjah Site - Roof", "Electrical Room", "Basement Pump Room", "Main Control Room"],
        "PPM Frequency": ["Quarterly", "Semi-Annual", "Monthly", "Monthly"]
    }
    st.dataframe(pd.DataFrame(equipment_data), use_container_width=True)
    
    st.write("---")
    st.subheader("2. PPM Task Execution Tracker")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        ppm_asset = st.selectbox("Select Equipment for PPM", ["AHU / FCU Units", "Main Distribution Board (MDB)", "Water Transfer Pumps", "Fire Alarm Panel"])
        ppm_type = st.selectbox("PPM Type", ["Monthly Inspection", "Quarterly Service", "Annual Overhaul"])
    with col_p2:
        tech_name = st.text_input("Assigned Technician / Team")
        ppm_status = st.selectbox("Status", ["Scheduled", "In-Progress", "Completed", "Pending Approval"])
        
    ppm_remarks = st.text_area("Technician Remarks / Parts Replaced")
    
    if st.button("Save PPM Log"):
        st.success(f"✅ PPM Log updated for {ppm_asset} - Status: {ppm_status}")
        
