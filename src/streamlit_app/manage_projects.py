import streamlit as st


options = st.session_state.db.list_projects()

st.title("Manage Projects")

with st.popover("Add project"):
    name = st.text_input("Project name")
    description = st.text_area("Description")
    if st.button("Add"):
        st.session_state.db.create_project(name, description)
        st.session_state.projects = st.session_state.db.list_projects()
        st.rerun()

