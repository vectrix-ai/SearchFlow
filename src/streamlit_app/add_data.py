import streamlit as st
import pandas as pd
from vectrix.importers import WebScraper, chunk_content

if "url" not in st.session_state:
    st.session_state.url = ""

if "urls" not in st.session_state:
    st.session_state.urls = []

st.title("Add Data")
st.subheader("Scrape website")
url = st.text_input("URL")
if st.button("Get all links"):
    st.session_state.url = url
    with st.spinner("Retrieving sitemap ..."):
        webscraper = WebScraper(url)
        st.session_state.urls = webscraper.get_all_links()

df = pd.DataFrame(
    {
        "links" : st.session_state.urls,
        "extract" : [True] * len(st.session_state.urls)
    }
)

if len(df) != 0:
    st.data_editor(
        data=df,
        column_config={"extract": st.column_config.CheckboxColumn(
            "Extract Webpage",
            help="Check to extract content from the webpage",
            default=True
        )},
        disabled=["links"],
        hide_index=True
    )

    if st.button("Add to database"):
        selected_links = df[df["extract"] == True]["links"].tolist()
        with st.spinner("Downloading pages ..."):
            webscraper = WebScraper(url)
            webscraper.download_pages(urls=selected_links, project_name=st.session_state.project)
            st.success("Data added to the database")
    
st.divider()
st.subheader('Upload Files')
uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True, type=[".pfd", ".doc", ".docx", ".txt"])
