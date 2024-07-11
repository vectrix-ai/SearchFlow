#!/usr/bin/env python
import os
from dotenv import load_dotenv

# Construct the path to the .env file located two directories above
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')

# Load the .env file using the constructed path
load_dotenv(dotenv_path)
os.environ["LANGCHAIN_TRACING_V2"] = "true"

print(os.getenv("LANGCHAIN_TRACING_V2"))

from typing import Union, List
from langchain.pydantic_v1 import BaseModel, Field

from fastapi import FastAPI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langserve import add_routes

# Declare a chain
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are a helpful, professional assistant named Cob."),
        MessagesPlaceholder(variable_name="messages"),
    ]
)

# Create chain
chain = prompt | ChatOpenAI()



class InputChat(BaseModel):
    """Input for the chat endpoint."""

    messages: List[Union[HumanMessage, AIMessage, SystemMessage]] = Field(
        ...,
        description="The chat messages representing the current conversation.",
    )


# App definition
app = FastAPI(
  title="LangChain Server",
  version="1.0",
  description="A simple API server using LangChain's Runnable interfaces",
)

# 5. Adding chain route
add_routes(
    app,
    chain.with_types(input_type=InputChat),
    enable_feedback_endpoint=True,
    enable_public_trace_link_endpoint=True,
    playground_type="chat",
    path="/chat",
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)