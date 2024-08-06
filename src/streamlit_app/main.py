import streamlit as st
from vectrix.db import Weaviate

st.logo("src/streamlit_app/assets/logo_small.png", link="https://vectrix.ai")


# Streamlit page configuration
chat_page = st.Page("chat.py", title="Ask", icon="💬")
add_data_page = st.Page("add_data.py", title="Add Data", icon="📝")
manage_projects = st.Page("manage_projects.py", title="Manage Projects", icon="📁")
view_sources = st.Page("view_sources.py", title="View Sources", icon="💾")


pg = st.navigation(
    {
        "Ask": [chat_page],
        "Manage Data": [add_data_page, view_sources],
        "Settings" : [manage_projects]
    }
    )



st.set_page_config(page_title="Vectrix RAG", page_icon="💬", layout="wide")


# Define the options for the dropdown
weaviate = Weaviate()
options = weaviate.list_collections()

# Add the dropdown to the sidebar
st.session_state["project"] = st.sidebar.selectbox("Choose a project:", options)


# Add an image to the sidebar, in the buttom 
pg.run()