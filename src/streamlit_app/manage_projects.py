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

@st.dialog('Remove project data')
def remove_project_data():
    st.write("Are you sure you want to remove all data from this project?")
    project = st.selectbox("Select project", st.session_state.projects)
    if st.button('Yes, remove all data', type="primary"):
        st.session_state.db.remove_project(project)
        #st.switch_page("main.py")
        st.session_state.projects = []
        st.session_state.project = ''
        st.rerun()

if len(st.session_state.projects) > 0:
    if st.button("Remove project data"):
        remove_project_data()
