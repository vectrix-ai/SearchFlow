import streamlit as st
import pandas as pd

# Database connection
SOURCES_DF = pd.DataFrame(st.session_state.db.get_collection_metdata(st.session_state.project)).drop_duplicates()

st.title("Sources")





st.subheader("Indexed Data")

if len(SOURCES_DF) == 0:
    st.warning("No sources indexed yet.")
else:
    st.subheader("Statistics 📊")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Documents", len(SOURCES_DF))
    col2.metric("Total Sources", SOURCES_DF['source_type'].nunique())
    col3.metric("Amount of formats", SOURCES_DF['source_format'].nunique())
    st.dataframe(SOURCES_DF[["url", "title", "source_type", "source_format", "language"]], 
                width=800,
                column_config={
                            "url" : st.column_config.LinkColumn(),
                        })
