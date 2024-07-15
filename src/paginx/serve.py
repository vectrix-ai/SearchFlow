from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Literal, Optional
from langchain_core.messages import HumanMessage
from paginx.graphs.vectrix import RAGWorkflowGraph
from paginx.db.postgresql import PostgresSaver
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

def transform_messages(messages: List[Message]):
    transformed = []
    for msg in messages:
        if msg.role == "user":
            transformed.append(HumanMessage(content=msg.content))
        elif msg.role == "system":
            transformed.append(SystemMessage(content=msg.content))
        elif msg.role == "assistant":
            transformed.append(AIMessage(content=msg.content))
    return transformed



async def stream_response(model: str, messages: List[Message], thread_id: Optional[str] = None):
    '''
    This function handles the streaming response for chat completions.

    Parameters:
    - model (str): The name of the model to use for chat completions.
    - messages (List[Message]): The list of messages in the conversation.
    - thread_id (Optional[str]): The ID of the conversation thread. If not provided, a new thread will be generated.

    Returns:
    - StreamingResponse: The streaming response containing the chat completions.

    Raises:
    - HTTPException: If the stream parameter is set to False.

    If you don't have a thread ID, we will generate one. But you have to pass the list of messages to keep track of the conversation.
    If you pass a thread_id, the graph will use the existing conversation context from the database.
    '''
    
    langchain_messages = transform_messages(messages)
    user_message = next((msg.content for msg in reversed(messages) if msg.role == "user"), None)

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    full_response = ""

    if model == 'vectrix':
        vectrix_model = RAGWorkflowGraph(DB_URI=DB_URI)
        graph = vectrix_model.create_graph(checkpointer=PostgresSaver(async_connection=pool))

        if thread_id:
            input_messages = {"question": user_message}

        else:
            langchain_messages.pop()
            input_messages = {"question": user_message, "messages": langchain_messages}
            thread_id = str(uuid.uuid4())

        async for event in graph.astream_events(
            {"question": user_message, "messages": langchain_messages}, 
            version="v1", 
            config = {"configurable": {"thread_id": thread_id}}):

            kind = event["event"]
            if kind == "on_chat_model_stream":
                if event['metadata']['langgraph_node'] == "generate_response":
                    content = event["data"]["chunk"].content
                    if content:
                        full_response += content
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': content}, 'index': 0, 'finish_reason': None}]})}\n\n"

        yield f"data: {json.dumps({'choices': [{'delta': {}, 'index': 0, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, chat_request: ChatCompletionRequest):
    if not chat_request.stream:
        raise HTTPException(status_code=400, detail="Only streaming responses are supported")

    return StreamingResponse(stream_response(chat_request.model, chat_request.messages), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)