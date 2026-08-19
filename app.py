import streamlit as st

st.set_page_config(page_title="EIFM Complaint Registrar", layout="centered")

st.title("📋 EIFM Complaint Registrar")
st.subheader("Register and Track Facilities Complaints")

st.write("---")

name = st.text_input("Name")
complaint = st.text_area("Describe your complaint")

if st.button("Submit Complaint"):
    if name and complaint:
        st.success("Complaint submitted successfully!")
    else:
        st.warning("Please fill out all fields.")
      
