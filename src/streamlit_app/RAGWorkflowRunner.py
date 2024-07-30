import asyncio
from langchain_core.messages import HumanMessage
from vectrix.graphs.basic_rag import RAGWorkflowGraph
from vectrix.db.checkpointer import PostgresSaver
from psycopg_pool import AsyncConnectionPool
from langsmith import Client

class RAGWorkflowRunner:
    def __init__(self, db_uri: str, thread_id: str):
        self.db_uri = db_uri
        self.thread_id = thread_id
        self.client = Client()
        self.run_id = ""
        self.retrieval_state = ""
        self.references = []

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

                async for event in graph.astream_events({"question": input_message}, version="v1", config=config):
                    self.run_id = event['run_id']
                    kind = event["event"]
                    if kind == "on_chat_model_stream":
                        if event['metadata']['langgraph_node'] == "generate_response":
                            content = event["data"]["chunk"].content
                            if content:
                                yield content
                        
                        new_state = event['metadata']['langgraph_triggers'][0].split(':')[-1]
                        if self.retrieval_state != new_state:
                            self.retrieval_state = new_state
                            status_callback(f"Running {new_state}...")
                    elif kind == "on_chain_end" and event["name"] == "generate_response":
                        if "documents" in event["data"]["input"]:
                            sources = [doc.dict() for doc in event["data"]["input"]["documents"]]
                            self.references.extend([source for source in sources])

            except Exception as e:
                raise RuntimeError(f"An error occurred: {str(e)}")

    def get_langsmith_run_url(self):
        run = self.client.read_run(self.run_id)
        return run.url

    def get_references(self):
        return self.references