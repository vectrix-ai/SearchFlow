import os
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from vectrix.db import DB
from vectrix import importers, logger

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

if __name__ == "__main__":
    import uvicorn
    if os.getenv('env') == 'localhost':
        uvicorn.run(
        "vectrix.api:app",
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

