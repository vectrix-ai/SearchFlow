from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from vectrix.graphs.utils.state import OverallState
from vectrix.graphs.utils.nodes import (
    detect_intent,
    decide_answering_path,
    llm_answer,
    split_question_list,
    retrieve,
    retrieve_documents,
    transform_docs,
    rag_answer,
    cite_sources
)
from vectrix import DB

db = DB()
projects = db.list_projects()

# Define the config
class GraphConfig(TypedDict):
    project_name: Literal[*projects]
    internet_search: bool

workflow = StateGraph(OverallState, config_schema=GraphConfig)

workflow.add_node("detect_intent", detect_intent)
workflow.add_node("llm_answer", llm_answer)
workflow.add_node("split_questions", split_question_list)
workflow.add_node("retrieve", retrieve)
workflow.add_node("transform_docs", transform_docs)
workflow.add_node("rag_answer", rag_answer)
workflow.add_node("cite_sources", cite_sources)




workflow.set_entry_point("detect_intent")
workflow.add_conditional_edges("detect_intent", decide_answering_path, {
    "greeting": "llm_answer",
    "specific_question": "split_questions",
    "metadata_query": END,
        "follow_up_question": "llm_answer"
})
workflow.add_edge("llm_answer", END)
workflow.add_conditional_edges("split_questions", retrieve_documents, ["retrieve"])
workflow.add_edge("retrieve", "transform_docs")
workflow.add_edge("transform_docs", "rag_answer")
workflow.add_edge("transform_docs", "cite_sources")
workflow.add_edge("rag_answer", END)
workflow.add_edge("cite_sources", END)
workflow.set_finish_point("rag_answer")

default_graph = workflow.compile()

__all__ = ['default_graph']