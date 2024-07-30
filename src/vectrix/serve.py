from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Literal, Optional, Union, AsyncGenerator
from langsmith import Client
from langchain_core.messages import HumanMessage
from vectrix.graphs.basic_rag import RAGWorkflowGraph
from vectrix.db.checkpointer import PostgresSaver
import json, os
from dotenv import load_dotenv
from pathlib import Path
from psycopg_pool import AsyncConnectionPool
import uuid
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# Load environment variables from .env file two directories above
env_path = Path(__file__).parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

os.environ["LANGCHAIN_TRACING_V2"] = "true"

app = FastAPI()
client = Client()

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = True
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None

# Database connection setup
DB_URI = os.getenv("DB_URI")
if not DB_URI:
    raise ValueError("DB_URI environment variable is not set")

# Shared connection pool for all requests
# This pool will be used across all user sessions
pool = AsyncConnectionPool(
    conninfo=DB_URI,
    max_size=20,  # Adjust this based on expected concurrent load
    open=False  # Prevent opening in constructor
)

@app.on_event("startup")
async def startup_event():
    await pool.open()
    checkpointer = PostgresSaver(async_connection=pool)
    await checkpointer.acreate_tables(pool)
    print(f"Connection pool opened with max size: {pool.max_size}")
@app.on_event("shutdown")
async def shutdown_event():
    await pool.close()
    print("Connection pool closed")

async def transform_messages(messages: List[Message]) -> List[Union[HumanMessage, SystemMessage, AIMessage]]:
    transformed = []
    for msg in messages:
        if msg.role == "user":
            transformed.append(HumanMessage(content=msg.content))
        elif msg.role == "system":
            transformed.append(SystemMessage(content=msg.content))
        elif msg.role == "assistant":
            transformed.append(AIMessage(content=msg.content))
    return transformed

async def get_user_message(messages: List[Message]) -> Optional[str]:
    return next((msg.content for msg in reversed(messages) if msg.role == "user"), None)

async def create_vectrix_graph(db_uri: str, pool) -> RAGWorkflowGraph:
    vectrix_model = RAGWorkflowGraph(DB_URI=db_uri)
    return vectrix_model.create_graph(checkpointer=PostgresSaver(async_connection=pool))

async def process_vectrix_event(event: dict, full_response: str) -> tuple:
    run_id = event['run_id']
    kind = event["event"]
    output = None

    if kind == "on_chat_model_stream":
        langgraph_trigger = event['metadata']['langgraph_triggers'][0].split(':')[-1]
        if event['metadata']['langgraph_node'] == "generate_response":
            content = event["data"]["chunk"].content
            if content:
                full_response += content
                output = json.dumps({
                    'choices': [{'delta': {'content': content}, 'index': 0, 'finish_reason': None}],
                    'langgraph_trigger': langgraph_trigger,
                    'run_id': run_id
                })
        else:
            output = json.dumps({
                'langgraph_trigger': langgraph_trigger,
                'run_id': run_id
            })
    elif kind == "on_chain_end" and event["name"] == "generate_response":
        if "documents" in event["data"]["input"]:
            sources = [doc.dict() for doc in event["data"]["input"]["documents"]]
            output = json.dumps({'sources': sources})

    return full_response, run_id, output

async def stream_vectrix_response(graph, input_messages: dict, thread_id: str) -> AsyncGenerator[str, None]:
    full_response = ""
    run_id = ""

    async for event in graph.astream_events(
        input_messages, 
        version="v1", 
        config={"configurable": {"thread_id": thread_id}}
    ):
        full_response, run_id, output = await process_vectrix_event(event, full_response)
        if output:
            yield f"data: {output}\n\n"

    # Final yield
    from langsmith import Client
    client = Client()
    yield f"data: {json.dumps({'choices': [{'delta': {}, 'index': 0, 'finish_reason': 'stop'}], 'run_id': run_id, 'langsmith_trace_url': client.read_run(run_id).url})}\n\n"
    yield "data: [DONE]\n\n"

async def stream_response(model: str, messages: List[Message], thread_id: Optional[str] = None, db_uri: str = None, pool=None) -> AsyncGenerator[str, None]:
    langchain_messages = await transform_messages(messages)
    user_message = await get_user_message(messages)

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    if model == 'vectrix':
        graph = await create_vectrix_graph(db_uri, pool)

        if not thread_id:
            langchain_messages.pop()
            thread_id = str(uuid.uuid4())

        input_messages = {
            "question": user_message,
            "messages": langchain_messages
        }

        async for output in stream_vectrix_response(graph, input_messages, thread_id):
            yield output
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported model: {model}")

# Usage in FastAPI route
@app.post("/v1/chat/completions")
async def chat_completions(request: Request, chat_request: ChatCompletionRequest):
    if not chat_request.stream:
        raise HTTPException(status_code=400, detail="Only streaming responses are supported")

    return StreamingResponse(
        stream_response(
            chat_request.model,
            chat_request.messages,
            db_uri=DB_URI,
            pool=pool
        ),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)