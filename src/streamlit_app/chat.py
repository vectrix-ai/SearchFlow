import asyncio
import uuid
import os
import re
import streamlit as st
from methods.RAGWorkflowRunner import RAGWorkflowRunner

from vectrix import logger

# Set up logging
logger = logger.setup_logger()

try:
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("dotenv not installed. Skipping loading of environment variables from .env file.")

# Configuration
DB_URI = os.getenv("DB_URI")
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "rag_runner" not in st.session_state:
    st.session_state.rag_runner = RAGWorkflowRunner(DB_URI, st.session_state.thread_id, project=st.session_state["project"])
if "final_output" not in st.session_state:
    st.session_state.final_output = {}

# Create two columns: one for chat, one for references
chat_col, ref_col = st.columns([2, 1])

def decode_unicode(text):
    def replace_unicode_escape(match):
        return chr(int(match.group(1), 16))
    
    return re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode_escape, text)

def reset_chat():
    st.session_state.messages = []
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.rag_runner = RAGWorkflowRunner(DB_URI, st.session_state.thread_id, project=st.session_state["project"])
    st.session_state.final_output = {}

with chat_col:
    st.title("Ask 💬")
    st.caption(f"Current Project: {st.session_state['project']}")
        
    # Add the yes/no toggle
    if "search_internet_toggle" not in st.session_state:
        st.session_state.search_internet_toggle = False
    st.session_state.search_internet_toggle = st.toggle("Enable Internet Search", st.session_state.search_internet_toggle)

    # Create a container for chat messages
    chat_container = st.container()

    # Create a container for the input box
    input_container = st.container()

    # Display chat messages in the chat container
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(decode_unicode(message["content"]))

    # Chat input at the bottom
    with input_container:
        prompt = st.chat_input("What would you like to know?")

    if prompt:
        # Add user message to chat history and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container.chat_message("user"):
            st.markdown(prompt)

        # Create a placeholder for the assistant's message
        with chat_container.chat_message("assistant"):
            message_placeholder = st.empty()

            # Create a status element
            status_element = st.empty()

            # Process the response
            with status_element.status("Processing...", expanded=False) as status:
                def update_status(message):
                    st.write(message)

                async def process_response():
                    full_response = ""
                    async for token in st.session_state.rag_runner.run(prompt, update_status):
                        full_response += token
                        message_placeholder.markdown(decode_unicode(full_response + "▌"))
                    message_placeholder.markdown(decode_unicode(full_response))
                    st.session_state.final_output = st.session_state.rag_runner.get_final_output()
                    return full_response

                # Run the async function
                full_response = asyncio.run(process_response())
                
                # Update the status: add the Langsmith Run URL and update to "Process complete"
                langsmith_url = st.session_state.rag_runner.get_trace_url()
                st.caption(f"[Langsmith trace]({langsmith_url})")
                status.update(label="Process complete!", state="complete", expanded=False)

            selected = st.feedback("thumbs")

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": decode_unicode(full_response)})

    if st.button("Reset Chat"):
        reset_chat()
        st.rerun()

with ref_col:
    st.subheader("References 📖")
    for i, reference in enumerate(st.session_state.final_output):
        with st.expander(f"Result {i+1}.", expanded=True):
            st.markdown(f"{reference['source'][:200].replace('\n', ' ')} ...")
            st.caption(f"Link: {reference['url']}")

