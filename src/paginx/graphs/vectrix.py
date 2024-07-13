from typing import List, Literal
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_cohere import CohereEmbeddings
from paginx.db.chroma import Chroma
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langgraph.graph.message import add_messages
from typing import Annotated
import os

class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    generation: str
    web_search: str
    documents: List[str]

class GradeDocuments(BaseModel):
    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )

class RAGWorkflowGraph:
    def __init__(self):
        # Initialize components
        self.retriever = self._setup_retriever()
        self.web_search_tool = TavilySearchResults(k=3)
        self.llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0, streaming=True)
        self.structured_llm_grader = self.llm.with_structured_output(GradeDocuments)
        self.rag_chain = self._setup_rag_chain()
        self.question_rewriter = self._setup_question_rewriter()

    def _setup_retriever(self):
        chroma = Chroma(CohereEmbeddings())
        vectorstore = chroma.load_db(os.getenv("CHROMA_DB_LOCATION"))
        return vectorstore.as_retriever()

    def _setup_rag_chain(self):
        prompt = hub.pull("rlm/rag-prompt")
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        return prompt | llm | StrOutputParser()

    def _setup_question_rewriter(self):
        system = """You a question re-writer that converts an input question to a better version that is optimized \n 
             for web search. Look at the input and try to reason about the underlying semantic intent / meaning."""
        re_write_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                (
                    "human",
                    "Here is the initial question: \n\n {question} \n Formulate an improved question.",
                ),
            ]
        )
        return re_write_prompt | self.llm | StrOutputParser()

    async def retrieve(self, state: GraphState) -> GraphState:
        question = state["messages"][-1].content


        docs = self.retriever.get_relevant_documents(question)

        state["documents"] = [doc.page_content for doc in docs]
        return state

    async def grade_documents(self, state: GraphState) -> GraphState:
        system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
            If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
            Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
        grade_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
            ]
        )
        retrieval_grader = grade_prompt | self.structured_llm_grader
        
        scores = []
        question = state["messages"][-1].content
        for doc in state["documents"]:
            result = await retrieval_grader.ainvoke({"question": question, "document": doc})
            scores.append(result.binary_score)
        
        state["relevance_scores"] = scores
        return state

    async def decide_to_generate(self, state: GraphState) -> Literal["transform_query", "generate"]:
        if any(score == "yes" for score in state["relevance_scores"]):
            return "generate"
        else:
            return "transform_query"

    async def generate(self, state: GraphState) -> GraphState:
        context = "\n\n".join(state["documents"])
        question = state["messages"][-1].content
        state["generation"] = await self.rag_chain.ainvoke({"context": context, "question": question})
        return state

    async def transform_query(self, state: GraphState) -> GraphState:
        question = state["messages"][-1].content
        state["question"] = await self.question_rewriter.ainvoke({"question": question})
        return state

    async def web_search(self, state: GraphState) -> GraphState:
        question = state["messages"][-1].content
        results = await self.web_search_tool.ainvoke(question)
        state["documents"] = [str(result) for result in results]
        return state

    def create_graph(self):
        workflow = StateGraph(GraphState)
        workflow.add_node("retrieve", self.retrieve)
        workflow.add_node("grade_documents", self.grade_documents)
        workflow.add_node("generate", self.generate)
        workflow.add_node("transform_query", self.transform_query)
        workflow.add_node("web_search_node", self.web_search)

        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_generate,
            {
                "transform_query": "transform_query",
                "generate": "generate",
            },
        )
        workflow.add_edge("transform_query", "web_search_node")
        workflow.add_edge("web_search_node", "generate")
        workflow.add_edge("generate", END)

        return workflow.compile()