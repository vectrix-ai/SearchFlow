import asyncio
from langchain_core.messages import HumanMessage
from vectrix.graphs.vectrix_advanced import Graph
from vectrix.graphs.checkpointer import PostgresSaver
from vectrix.streaming.processor import StreamProcessor
from psycopg_pool import AsyncConnectionPool

class RAGWorkflowRunner:
    def __init__(self, db_uri: str, thread_id: str, project: str):
        self.db_uri = db_uri
        self.thread_id = thread_id
        self.run_id = ""
        self.retrieval_state = ""
        self.final_output = {}
        self.trace_url = ""
        self.project = project

    async def run(self, prompt: str, status_callback: callable):
         # Reset references at the start of each run
        
        async with AsyncConnectionPool(conninfo=self.db_uri) as pool:
            try:
                checkpointer = PostgresSaver(async_connection=pool)
                await checkpointer.acreate_tables(pool)

                config = {"configurable": {"thread_id": self.thread_id}}
                graph = Graph(DB_URI=self.db_uri, project=project)
                graph = graph.create_graph(checkpointer=checkpointer)

                input_message = HumanMessage(content=prompt)
                self.references = []

                stream_processor = StreamProcessor(config)
                
                async for event in stream_processor.process_stream(graph, input_message):
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