import streamlit as st
from vectrix.importers import WebCrawler, ChunkData
from vectrix.db import Weaviate

weaviate = Weaviate()

st.title("Add Data")
st.subheader("Scrape website")
url = st.text_input("URL")
startswith = st.text_input("URL must start with (optional)", value=url)

def scrape_website():
    crawler = WebCrawler(url, startswith=startswith if startswith else url)
    documents = []
    
    for item in crawler.extract():
        if isinstance(item, dict):
            # This is a status update
            yield item
        else:
            # This is the final list of documents
            documents.extend(item)
    
    if documents:
        chunked_webdata = ChunkData.chunk_content(documents, chunk_size=500, chunk_overlap=50)
        weaviate.set_colleciton(st.session_state["project"])
        weaviate.add_data(chunked_webdata)
        return f"Scraping completed, extracted {len(documents)} pages"
    else:
        return "No documents were extracted. Please check the URL and try again."

if st.button("Submit"):
    with st.status("Scraping website...", expanded=True) as status:
        pages_scraped = st.empty()
        links_remaining = st.empty()
        
        for result in scrape_website():
            if isinstance(result, dict):
                status.update(label=f"Status: {result['status']}", state="running")
                if 'pages_scraped' in result:
                    pages_scraped.text(f"Pages scraped: {result['pages_scraped']}")
                if 'links_remaining' in result:
                    links_remaining.text(f"Links remaining: {result['links_remaining']}")
            else:
                # Final result
                if "completed" in result.lower():
                    status.update(label=result, state="complete")
                else:
                    status.update(label=result, state="error")

st.divider()
st.subheader("Upload file")
uploaded_file = st.file_uploader("Choose a file")

st.divider()
st.subheader("Load from OneDrive ☁️")
