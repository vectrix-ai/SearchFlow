from typing import List, Tuple
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain import hub
from langgraph.graph.message import add_messages
from typing import Annotated
from langchain.schema import Document
from paginx.db.postgresql import BaseCheckpointSaver
from paginx.db.vector_retriever import Retriever



class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    generation: str
    web_search: str
    documents: List[Tuple[Document, float]]
    question: str

class GradeDocuments(BaseModel):
    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )

class RAGWorkflowGraph:
    def __init__(self, DB_URI: str):
        # Initialize components
        self.DB_URI = DB_URI
        self.retriever = Retriever(retriever="chroma").get_retriever()
        self.web_search_tool = TavilySearchResults(k=3)
        self.llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0, streaming=True)
        self.rag_chain = self._setup_rag_chain()
        self.question_rewriter = self._setup_question_rewriter()
        self.retrieval_grader = self._setup_retrieval_grader()


    def _setup_rag_chain(self):
        prompt = hub.pull("rlm/rag-prompt")
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        return prompt | llm | StrOutputParser()

    def _setup_question_rewriter(self):
        re_write_prompt = hub.pull("joeywhelan/rephrase")
        return re_write_prompt | self.llm | StrOutputParser()
    
    def _setup_retrieval_grader(self):
        system = """You are a grader assessing relevance of a retrieved document to a user question. \n 
            If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant. \n
            Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question."""
        
        grade_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system),
                ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
            ]
        )

        structured_llm_grader = self.llm.with_structured_output(GradeDocuments)
        return grade_prompt | structured_llm_grader
    
    async def transform_query(self, state):
        '''
        Transform the query to procude a better question

        Agrs:
            state: GraphState


        Returns:
            state (dict): Updates question key with a re-phrased question
        '''    

        question = state['question']
        chat_history = state['messages']

        # Rewrite the question
        better_question = await self.question_rewriter.ainvoke({"input": question, "chat_history" : chat_history})
        return {"question": better_question, "messages": question}
    

    async def retrieve(self, state):
        '''
        Retrieve documents relevant to the question

        Args:
            state: GraphState

        Returns:
            state (dict): Updates documents key with relevant documents
        '''
        question = state['question']
        documents_with_scores = await self.retriever.ainvoke(question)
        return {"documents": documents_with_scores}
    
    async def grade_documents(self, state):
        '''
        Grade the relevance of the retrieved documents to the question

        Args:
            state: GraphState

        Returns:
            state (dict): The filtered documents, web_search (yes/no)
        '''

        question = state['question']
        documents_with_scores = state['documents']

        filtered_docs = []
        web_search = "No"

        for doc, score in documents_with_scores:
            score  = await self.retrieval_grader.ainvoke({"document": doc.page_content, "question": question})
            grade = score.binary_score

            if grade == "yes":
                filtered_docs.append(doc)

        if len(filtered_docs) == 0:
            web_search = "Yes"

        return {"documents": filtered_docs, "web_search": web_search}
    

    async def decide_to_search_web(self, state):
        '''
        Decide whether to search the web for more documents

        Args:
            state: GraphState

        Returns:
            state (dict): The web_search key is updated with 'generate' or 'web_search'
        '''

        web_search = state['web_search']
        if web_search == "Yes":
            return "web_search"
        else:
            return "generate"
        

    async def search_web(self, state):
        '''
        Search the web for more documents

        Args:
            state: GraphState

        Returns:
            state (dict):  Updates documents key with appended web results
        '''

        question = state['question']
        documents = state['documents']

        docs = await self.web_search_tool.ainvoke({"query": question})
        web_results = "\n".join([d["content"] for d in docs])
        web_results = Document(page_content=web_results)
        documents.append(web_results)

        return {"documents": documents}
    

    async def generate_response(self, state):
        '''
        Generate a response to the user

        Args:
            state: GraphState

        Returns:
            state (dict): The generation key is updated with the response
        '''

        documents = state['documents']
        question = state['question']

        response = await self.rag_chain.ainvoke({"context": documents, "question": question})
        return {"generation": response}
    

    def create_graph(self, checkpointer: BaseCheckpointSaver):
        workflow = StateGraph(GraphState)
        workflow.add_node("retrieve", self.retrieve)  # retrieve
        workflow.add_node("grade_documents", self.grade_documents)  # grade documents
        workflow.add_node("generate_response", self.generate_response)  # generatae
        workflow.add_node("transform_query", self.transform_query)  # transform_query
        workflow.add_node("search_web", self.search_web)  # web search

        workflow.add_edge(START, "transform_query")
        workflow.add_edge("transform_query", "retrieve")
        workflow.add_edge("retrieve", "grade_documents")
        workflow.add_conditional_edges(
            "grade_documents",
            self.decide_to_search_web,
            {
                "web_search": "search_web",
                "generate": "generate_response",
            },
        )
        workflow.add_edge("search_web", "generate_response")
        workflow.add_edge("generate_response", END)

        return workflow.compile(checkpointer=checkpointer)






    