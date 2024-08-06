import streamlit as st
from vectrix.db import Weaviate
import pandas as pd


# Database connection
weaviate = Weaviate()
weaviate.set_colleciton(st.session_state["project"])
SOURCES_DF = pd.DataFrame(weaviate.list_metadata()).drop_duplicates()

st.title("Sources")
st.subheader("Statistics 📊")
col1, col2, col3 = st.columns(3)
col1.metric("Total Documents", len(SOURCES_DF))
col2.metric("Total Sources", SOURCES_DF['source_type'].nunique())
col3.metric("Amount of formats", SOURCES_DF['source_format'].nunique())




st.subheader("Indexed Data")

st.dataframe(SOURCES_DF, 
            width=800,
            column_config={
                        "url" : st.column_config.LinkColumn(),
                    })