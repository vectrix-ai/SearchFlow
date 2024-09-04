import streamlit as st

options = st.session_state.db.list_projects()

st.title("Manage Projects")

@st.dialog('Add project')
def add_project():
    name = st.text_input("Project name")
    description = st.text_area("Description")
    if st.button("Add"):
        st.session_state.db.create_project(name, description)
        st.session_state.projects = st.session_state.db.list_projects()
        st.rerun()

@st.dialog('Remove project data')
def remove_project_data():
    st.write("Remove the project and all the linked data")
    project = st.selectbox("Select project", st.session_state.projects)
    if st.button('Yes, remove the project and all data', type="primary"):
        st.session_state.db.remove_project(project)
        st.session_state.projects = st.session_state.db.list_projects()
        st.session_state.project = st.session_state.db.list_projects()[0]
        st.rerun()

col1, col2 = st.columns(2)


with col1:
    if st.button("Add project", use_container_width=True):
        add_project()

with col2:
    if len(st.session_state.projects) > 0:
        if st.button("Remove project", type="primary", use_container_width=True):
            remove_project_data()

