import asyncio
from langchain_core.messages import HumanMessage
from vectrix.graphs.basic_rag import RAGWorkflowGraph
from vectrix.db.checkpointer import PostgresSaver
from vectrix.streaming.processor import StreamProcessor
from psycopg_pool import AsyncConnectionPool
from langsmith import Client

class RAGWorkflowRunner:
    def __init__(self, db_uri: str, thread_id: str):
        self.db_uri = db_uri
        self.thread_id = thread_id
        self.client = Client()
        self.run_id = ""
        self.retrieval_state = ""
        self.final_output = {}

    async def run(self, prompt: str, status_callback: callable):
         # Reset references at the start of each run
        
        async with AsyncConnectionPool(conninfo=self.db_uri) as pool:
            try:
                checkpointer = PostgresSaver(async_connection=pool)
                await checkpointer.acreate_tables(pool)

                config = {"configurable": {"thread_id": self.thread_id}}
                demo_graph = RAGWorkflowGraph(DB_URI=self.db_uri)
                graph = demo_graph.create_graph(checkpointer=checkpointer)

                input_message = HumanMessage(content=prompt)
                self.references = []

                stream_processor = StreamProcessor(config)
                
                async for event in stream_processor.process_stream(graph, input_message):
                    self.run_id = event['run_id']
                    if event['type'] == 'response':
                        yield event['chunk_content']

                    if event['type'] == 'progress':
                        status_callback(f"Running {event['status']}...")

                    if event['type'] == 'final_output':
                        self.final_output = event

            except Exception as e:
                raise RuntimeError(f"An error occurred: {str(e)}")



    def get_final_output(self):
        return self.final_output