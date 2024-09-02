import streamlit as st
import pandas as pd
from searchflow.importers import WebScraper
import pandas as pd

if "url" not in st.session_state:
    st.session_state.url = ""

if "urls" not in st.session_state:
    st.session_state.urls = []


st.title("Scrape Data 🔍")
st.subheader("Detect links")
st.info("Detect all links in a website and add them to the import queue.")
url = st.text_input("Enter website URL")
if st.button("Submit"):
    try:
        st.success("Scraping job submitted")
        scraper = WebScraper(project_name=st.session_state.project)
        scraper.get_all_links(base_url=url)
        
    except Exception as e:
        st.error(f"Error: {e}")
    

st.subheader('Scrape job status')
scrape_job_status = pd.DataFrame(st.session_state.db.get_indexing_status(project_name=st.session_state.project))
if len(scrape_job_status) > 0:
    st.dataframe(scrape_job_status, hide_index=True)
else:
    st.warning("No sites imported")


st.subheader('Links to confirm')

webscraper = WebScraper(project_name=st.session_state.project)

@st.dialog("Import a single webpage")
def import_webpage():
    url = st.text_input("URL")
    if st.button("Import"):
        st.session_state.db.add_links_to_index(links=[url], project_name=st.session_state.project, base_url=url, status="Confirm page import")
        st.success("Webpage added to import queue")
        st.rerun()

if st.button("Add a page to import queue"):
    import_webpage()


links_to_confirm = pd.DataFrame(st.session_state.db.get_links_to_confirm(project_name=st.session_state.project))
if len(links_to_confirm) > 0:
    links_to_confirm['Extract'] = True
    st.data_editor(
        data=links_to_confirm,
        column_config={"Extract": st.column_config.CheckboxColumn(
                "Extract Webpage",
                help="Check to extract content from the webpage",
                default=True
            )},
        disabled=['url', 'base_url'],
        hide_index=True,
    )
    if st.button('Confirm page import'):
        selected_links = links_to_confirm[links_to_confirm['Extract'] == True]['url'].tolist()
        st.success('Sraping job submitted')
        webscraper.download_pages(urls=selected_links, project_name=st.session_state.project)
else:
    st.warning("No links to confirm")

st.subheader('Full Site Import')
st.info("""
        We use an external crawler to index the full website at once.\n
        Please be carefull with the max pages setting.""")
url = st.text_input("URL")
max_pages = st.number_input("Max pages", min_value=1, max_value=3000, value=100)

if st.button("Submit", key="full_import_submit"):
    with st.spinner('Importing full site'):
        try:
            webscraper.full_import(url=url, max_pages=int(max_pages))
            st.success("Full site import submitted")
        except Exception as e:
            st.error(f"Error: {e}")

