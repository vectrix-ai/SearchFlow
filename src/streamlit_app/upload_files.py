import uuid
import os
import streamlit as st
import pandas as pd
from searchflow.importers import Files

files = Files()

st.header('Upload Files')
uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True, type=[".pdf", ".doc", ".docx", ".txt"])

# Add a submit button
if st.button('Submit'):
    if uploaded_files:
        st.text("Uploading files...")
        progress_bar = st.progress(0)
        total_files = len(uploaded_files)
        
        for i, file in enumerate(uploaded_files):
            bytes_data = file.read()
            # Store locally in a temp folder
            # Empty the uploaded files variable
            files.upload_file(
                document_data=[(bytes_data, file.name)],
                project_name=st.session_state.project,
                inference_type="local"
            )

            # Now remove the local file and folder
            # Update progress bar
            progress_bar.progress((i + 1) / total_files)

        # Clean the list of files
        st.session_state.uploaded_files = None
        st.success("Files uploaded successfully!")
        st.rerun()

st.subheader('Uploaded Files')
uploaded_files = st.session_state.db.list_files(st.session_state.project)
if len(uploaded_files) > 0:
    df = pd.DataFrame(uploaded_files)
    st.dataframe(
        df[["filename", "creation_date", "update_date", "signed_download_url"]], 
        hide_index=True,
        column_config={
            "signed_download_url": st.column_config.LinkColumn(
                display_text="Open File",
            )
        },
        use_container_width=True
        )
    file_to_remove = st.selectbox("Select a file to remove", df['filename'])
    if st.button('Remove File', type='primary'):
        if file_to_remove:
            st.session_state.db.remove_file(st.session_state.project, file_to_remove)
            st.error("File removed successfully!")
            st.rerun()
else:
    st.warning("No files uploaded yet.")


