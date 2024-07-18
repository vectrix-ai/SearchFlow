# about_page.py

import streamlit as st

def about_page():
    st.title("About Vectrix")
    
    st.write("""
    Vectrix is an AI-powered chat application that uses advanced language models and 
    retrieval-augmented generation (RAG) to provide informative and context-aware responses.
    
    Key features:
    - Natural language conversations with AI
    - Real-time reference retrieval
    - Multi-page Streamlit interface
    
    This application demonstrates the power of combining large language models with 
    efficient information retrieval techniques to enhance the quality and accuracy of AI-generated responses.
    """)
    
    st.subheader("How it works")
    st.write("""
    1. User inputs a question or prompt
    2. The system searches a knowledge base for relevant information
    3. Retrieved information is used to augment the AI's knowledge
    4. The AI generates a response based on its training and the augmented information
    5. References are displayed alongside the chat for transparency
    """)
    
    st.subheader("Technologies Used")
    st.write("""
    - Streamlit: For the web interface
    - LangChain: For RAG workflows
    - Large Language Models: For natural language understanding and generation
    - Vector Databases: For efficient information retrieval
    """)