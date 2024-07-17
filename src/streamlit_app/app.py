import asyncio
import uuid
import os
from dotenv import load_dotenv
import streamlit as st
from RAGWorkflowRunner import RAGWorkflowRunner

# Load environment variables
load_dotenv()

# Configuration
DB_URI = os.getenv("DB_URI")
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Streamlit page configuration
st.set_page_config(page_title="Vectrix RAG Chat with search", page_icon="💬")
st.title("Vectrix Chat 💬")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "rag_runner" not in st.session_state:
    st.session_state.rag_runner = RAGWorkflowRunner(DB_URI, st.session_state.thread_id)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
prompt = st.chat_input("What would you like to know?")

if prompt:
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Create a status element above the assistant's message
    status_element = st.empty()

    # Initialize the assistant's message placeholder
    assistant_placeholder = st.empty()

    # Process the response
    with status_element.status("Processing...", expanded=True) as status:
        def update_status(message):
            st.write(message)

        async def process_response():
            full_response = ""
            async for token in st.session_state.rag_runner.run(prompt, update_status):
                full_response += token
                with assistant_placeholder.chat_message("assistant"):
                    st.markdown(full_response + "▌")
            with assistant_placeholder.chat_message("assistant"):
                st.markdown(full_response)
            return full_response

        # Run the async function
        full_response = asyncio.run(process_response())
        
        # Update the status: add the Langsmith Run URL and update to "Process complete"
        langsmith_url = st.session_state.rag_runner.get_langsmith_run_url()
        st.caption(f"[Langsmith trace]({langsmith_url})")
        status.update(label="Process complete!", state="complete", expanded=False)

    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Display references
    with st.expander('References 📖'):
        for reference in st.session_state.rag_runner.get_references():
            st.caption(reference)