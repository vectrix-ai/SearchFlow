import streamlit as st

st.subheader('Upload Files')
uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True, type=[".pfd", ".doc", ".docx", ".txt"])