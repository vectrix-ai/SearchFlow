import asyncio
import uuid
import os
import re
from dotenv import load_dotenv
import streamlit as st
from RAGWorkflowRunner import RAGWorkflowRunner

# Load environment variables
load_dotenv()

# Configuration
DB_URI = os.getenv("DB_URI")
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Streamlit page configuration
st.set_page_config(page_title="Vectrix RAG Chat with search", page_icon="💬", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "rag_runner" not in st.session_state:
    st.session_state.rag_runner = RAGWorkflowRunner(DB_URI, st.session_state.thread_id)
if "final_output" not in st.session_state:
    st.session_state.final_output = {}

# Create two columns: one for chat, one for references
chat_col, ref_col = st.columns([2, 1])

def decode_unicode(text):
    def replace_unicode_escape(match):
        return chr(int(match.group(1), 16))
    
    return re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode_escape, text)


with chat_col:
    st.title("Vectrix 💬")

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
            with status_element.status("Processing...", expanded=True) as status:
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
                langsmith_url = st.session_state.final_output['trace_url']
                st.caption(f"[Langsmith trace]({langsmith_url})")
                status.update(label="Process complete!", state="complete", expanded=False)

        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": decode_unicode(full_response)})

with ref_col:
    st.subheader("References 📖")
    if 'sources' in st.session_state.final_output:
        for i, reference in enumerate(st.session_state.final_output['sources']['references']):
            with st.expander(f"Result {i+1}.", expanded=True):
                st.markdown(f"{reference['text'].replace('\n', ' ')} ...")
                st.caption(f"Link: {reference['url']}")
    else:
        st.write("No references available yet.")