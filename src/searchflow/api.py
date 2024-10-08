import os
import time
from typing import List
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
from searchflow.db import DB
from searchflow import importers, logger

db = DB()

app = FastAPI(
    title="SearchFlow API",
    version="1.0.0",
    description="API for receiving and processing captured HTML content"
)

logging = logger.setup_logger(name="API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class HTMLContent(BaseModel):
    url: str
    html: str
    project_name: str

class APIResponse(BaseModel):
    success: bool
    message: str
    contentLength: int

@app.post("/chrome_capture", response_model=APIResponse)
async def receive_html(content: HTMLContent):
    try:
        html_content = content.html
        project_name = content.project_name
        url = content.url
        content_length = len(html_content)

        chrome_importer = importers.ChromeImporter(project_name, db=db)
        chrome_importer.add_web_page(html_content, url)
        
        print(project_name)
        # Here you can add your processing logic for the HTML content
        # For example, you might want to store it in a database or process it further
        # You can now use the project_name in your processing logic
        
        return APIResponse(
            success=True,
            message=f"HTML content received and processed successfully for project: {project_name}",
            contentLength=content_length
        )
    except Exception as e:
        logging.error(f"Error processing HTML content: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/projects", response_model=List[str])
async def get_projects():
    return db.list_projects()


@app.get("/models/1")
async def models(authorization: str = Header(None)):
    json = {
        "object": "list",
        "data": [
            {
                "id": "searchflow-test1-graph-model",
                "object": "model",
                "created": 1686935002,
                "owned_by": "organization-owner"
            },
            {
                "id": "searchflow-test2-graph-model",
                "object": "model",
                "created": 1686935002,
                "owned_by": "organization-owner",
            },
            {
                "id": "searchflow-test3-graph-model",
                "object": "model",
                "created": 1686935002,
                "owned_by": "openai"
            },
        ],
        "object": "list"
    }
    return JSONResponse(content=json)



@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    # Parse the incoming JSON request
    data = await request.json()
    
    # Extract relevant information (not used in this dummy response)
    messages = data.get("messages", [])
    model = data.get("model", "default_model")
    
    # Prepare a dummy response
    dummy_response = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a dummy response from the SearchFlow API."
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 9,
            "completion_tokens": 12,
            "total_tokens": 21
        }
    }
    
    return JSONResponse(content=dummy_response)

if __name__ == "__main__":
    import uvicorn
    if os.getenv('env') == 'localhost':
        uvicorn.run(
        "searchflow.api:app",
        host="0.0.0.0", 
        port=8000,
        ssl_keyfile='localhost-key.pem',
        ssl_certfile='localhost.pem',
        reload=True  # Enable hot reloading
    )
    else:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000
        )

