from typing import Annotated, Literal, AsyncIterator, Dict, Any
from typing_extensions import TypedDict
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from langgraph.graph.message import add_messages
from langchain_core.messages import AIMessage

class State(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def search(query: str):
    """Call to surf the web."""
    return ["Cloudy with a chance of hail."]

class DemoGraph:
    def __init__(self) -> None:
        tools = [search]
        self.model = ChatOpenAI(model="gpt-3.5-turbo", streaming=True).bind_tools(tools)

    def should_continue(self, state: State) -> Literal["__end__", "tools"]:
        messages = state["messages"]
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and not last_message.additional_kwargs.get("tool_calls"):
            return END
        else:
            return "tools"

    async def call_model(self, state: State, config: RunnableConfig):
        messages = state["messages"]
        response = await self.model.ainvoke(messages, config)
        return {"messages": response}

    async def stream_events(self, state: State) -> AsyncIterator[Dict[str, Any]]:
        messages = state["messages"]
        async for event in self.model.astream_events(messages, version="v1"):
            kind = event["event"]
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield {"type": "token", "content": content}
            elif kind == "on_tool_start":
                yield {
                    "type": "tool_start",
                    "tool": event["name"],
                    "input": event["data"].get("input")
                }
            elif kind == "on_tool_end":
                yield {
                    "type": "tool_end",
                    "tool": event["name"],
                    "output": event["data"].get("output")
                }

    def create_graph(self):
        workflow = StateGraph(State)
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools", ToolNode(tools=[search]))
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
        )
        workflow.add_edge("tools", "agent")
        return workflow.compile()
    

    