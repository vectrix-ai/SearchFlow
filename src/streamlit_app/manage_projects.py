import streamlit as st
from vectrix.db import Weaviate


weaviate = Weaviate()
options = weaviate.list_collections()

st.title("Manage Projects")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Add Project")
    project_name = st.text_input("Enter project name")
    embedding_model = st.selectbox("Select embedding model", ["Ollama", "OpenAI"])
    model_name = st.selectbox("Select model name", ["mxbai-embed-large:335m"])
    model_url = st.text_input(label="Embedding Model URL", value="http://host.docker.internal:11434")

    print(model_name)
    if st.button("Add Project", use_container_width=True):
        weaviate.create_collection(
            name=project_name,
            embedding_model=embedding_model,
            model_name=model_name,
            model_url=model_url)
        st.session_state["project"].append(project_name)
        st.success("Project added successfully!")
        # Refresh the app
        
        

with col2:
    st.subheader("Remove Project")
    project_to_remove = st.selectbox("Select a project to remove", options )
    if st.button("Remove Project", type="primary", use_container_width=False):
        weaviate.remove_collection(project_to_remove)
        st.success("Project removed successfully!")
        st.rerun()
