import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from vectrix.graphs import default_graph
#from vectrix.graphs.checkpointer import PostgresSaver
from vectrix.streaming.processor import StreamProcessor
import streamlit as st


class RAGWorkflowRunner:
    def __init__(self, thread_id: str, project: str):
        self.thread_id = thread_id
        self.run_id = ""
        self.retrieval_state = ""
        self.final_output = {}
        self.trace_url = ""
        self.project = project

    async def run(self, prompt: str, status_callback: callable):
         # Reset references at the start of each run
        try:
            #checkpointer = PostgresSaver()
            st.session_state.logger.warning("Creating graph for project %s", st.session_state['project'])
            input_message = HumanMessage(content=prompt)
            self.references = []

            stream = StreamProcessor(graph=default_graph, project_name=st.session_state['project'], internet_search=st.session_state.search_internet_toggle)

            
            async for event in stream.process_stream(messages=st.session_state["messages"]):
                self.run_id = event['run_id']
                if event['type'] == 'stream':
                    yield event['data']

                if event['type'] == 'progress':
                    status_callback(event['data'])

                if event['type'] == 'final_output':
                    self.final_output = event['data']
                    self.trace_url = event['trace_url']

        except Exception as e:
            raise RuntimeError(f"An error occurred: {str(e)}")



    def get_final_output(self):
        return self.final_output
    
    def get_trace_url(self):
        return self.trace_url