from dotenv import load_dotenv
load_dotenv()
import streamlit as st
from vectrix.db import DB
from vectrix import logger



st.session_state.logger = logger.setup_logger(name="Streamlit App", level="ERROR")

if "project" not in st.session_state:
    st.session_state.project = ''

if "db" not in st.session_state:
    st.session_state.db = DB()

if "projects" not in st.session_state:
    st.session_state.projects = st.session_state.db.list_projects()

def select_project():
    
    if len(st.session_state.projects) == 0:
        st.sidebar.warning("No projects available. Please create a project first.")
        return None
    
    project = st.sidebar.selectbox(
        "Choose a project:", 
        st.session_state.projects,
        key="project_selector_unique"
    )

    st.session_state.logger.warning(f"Selected project: {project}")
    
    st.session_state.project = project
    if st.sidebar.button('Refresh Sources 🔁'):
        st.rerun()
    return project

st.logo("src/streamlit_app/assets/logo_small.png", link="https://vectrix.ai")

# Streamlit page configuration
chat_page = st.Page("chat.py", title="Ask", icon="💬")
scrape_data = st.Page("scrape_data.py", title="Scrape Website", icon="🔍")
manage_projects = st.Page("manage_projects.py", title="Manage Projects", icon="📁")
upload_files = st.Page("upload_files.py", title="Upload Files", icon="⬆️")
manage_sources = st.Page("manage_sources.py", title="Manage Sources", icon="📚")

if len(st.session_state.projects) == 0:
    pg = st.navigation(
        {
            "Settings" : [manage_projects]
        }
    )
else:
     pg = st.navigation(
        {
            "Ask": [chat_page],
            "Sources": [scrape_data, upload_files, manage_sources],
            "Settings" : [manage_projects]
        },
    )

st.set_page_config(page_title="Vectrix Assistant", page_icon="💬", layout="wide")

# Call select_project() before pg.run()

select_project()

pg.run()
