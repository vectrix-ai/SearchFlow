# about_page.py

import streamlit as st
from vectrix.importers import WebCrawler, ChunkData
from vectrix.db import Weaviate
weaviate = Weaviate()


st.title("Add Data")
st.subheader("Scrape website")
url = st.text_input("URL")

if st.button("Submit"):
    with st.spinner("Scraping website..."):
        crawler = WebCrawler(url)
        extracted_pages = crawler.extract()
        chunked_webdata = ChunkData.chunk_content(extracted_pages, chunk_size=500, chunk_overlap=50)
        weaviate.set_colleciton(st.session_state["project"])
        weaviate.add_data(chunked_webdata)

        st.success(f"Scraping completed, extracted {len(extracted_pages)} pages")

st.divider()
st.subheader("Upload file")
uploaded_file = st.file_uploader("Choose a file")

st.divider()
st.subheader("Load from OneDrive ☁️")
