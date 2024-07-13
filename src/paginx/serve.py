
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Literal, Optional
from langchain_core.messages import HumanMessage
from paginx.graphs.demo import DemoGraph
from paginx.graphs.vectrix import RAGWorkflowGraph
import json, os
from dotenv import load_dotenv
from pathlib import Path


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

demo_graph = DemoGraph()
demo_model = demo_graph.create_graph()

async def stream_response(model: str, messages: List[Message]):
    user_message = next((msg.content for msg in reversed(messages) if msg.role == "user"), None)
    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    inputs = [HumanMessage(content=user_message)]
    full_response = ""

    if model == 'demo':
        demo_graph = DemoGraph()
        demo_model = demo_graph.create_graph()
        async for event in demo_model.astream_events({"messages": inputs}, version="v1"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': content}, 'index': 0, 'finish_reason': None}]})}\n\n"

        yield f"data: {json.dumps({'choices': [{'delta': {}, 'index': 0, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"


    if model == 'vectrix':
        vectrix_model = RAGWorkflowGraph()
        vectrix_model = vectrix_model.create_graph()
        async for event in vectrix_model.astream_events({"messages": inputs}, version="v1"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': content}, 'index': 0, 'finish_reason': None}]})}\n\n"

        yield f"data: {json.dumps({'choices': [{'delta': {}, 'index': 0, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if not request.stream:
        raise HTTPException(status_code=400, detail="Only streaming responses are supported")

    return StreamingResponse(stream_response(request.model, request.messages), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)