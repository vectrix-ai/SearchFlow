import logging
import operator
from typing import List, Tuple, Annotated
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain import hub
from langgraph.graph.message import add_messages
from langgraph.constants import Send
from langchain.schema import Document
from langchain.output_parsers.openai_tools import PydanticToolsParser
from langchain_community.tools.tavily_search import TavilySearchResults
from vectrix.graphs.checkpointer import BaseCheckpointSaver
from vectrix.db.weaviate import Weaviate

class QuestionList(BaseModel):
    questions: List[str] = Field(
        description="List of questions to ask the user"
    )

class GradeDocuments(BaseModel):
    binary_score: str = Field(
        description="Documents are relevant to the question, 'yes' or 'no'"
    )

class CitedSources(BaseModel):
    source: str = Field(
        description="The source of the information"
    )
    url: str = Field(
        description="The URL associated with the source"
    )


class OverallState(TypedDict):
    messages: Annotated[list, add_messages]
    question: str
    question_list : List[str]
    documents: Annotated[list, operator.add]
    graded_documents: Annotated[list, operator.add]
    web_search: str
    llm_response: str
    cited_sources: List[CitedSources]

class QuestionState(TypedDict):
    question: str

class DocumentState(TypedDict):
    document: Document
    question: str

class Graph:
    def __init__(self, DB_URI: str, project: str):
        # Initialize components
        self.DB_URI = DB_URI
        weaviate = Weaviate()
        weaviate.set_colleciton(project)
        self.retriever = weaviate.get_retriever()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.question_rewriter = self._setup_question_rewriter()
        self.question_alternatives = self._setup_question_alternatives()
        self.retrieval_grader = self._setup_retrieval_grader()
        self.web_search_tool = TavilySearchResults()
        self.answer_question_chain = self._setup_answer_question_chain()
        self.cite_sources_chain = self._setup_cite_sources_chain()
        self.logger = logging.getLogger(__name__)

    def _setup_question_rewriter(self):
        re_write_prompt = hub.pull("joeywhelan/rephrase")
        return re_write_prompt | self.llm | StrOutputParser()
    
    def _setup_question_alternatives(self):
        llm = self.llm.bind_tools(tools=[QuestionList])
        prompt = hub.pull("alternative_questions")
        return prompt | llm | PydanticToolsParser(tools=[QuestionList])
    
    def _filter_duplicate_docs(self, documents : List[Document]) -> List[Document]:
        seen_uuids = set()
        unique_documents = []
        for doc in documents:
            uuid = doc.metadata.get('uuid')
            if uuid not in seen_uuids:
                seen_uuids.add(uuid)
                unique_documents.append(doc)

        return unique_documents
    

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

        llm_with_tools = self.llm.bind_tools([GradeDocuments])
        parser = PydanticToolsParser(tools=[GradeDocuments])

        grade_chain = grade_prompt | llm_with_tools | parser
        return grade_chain
    
    def _setup_answer_question_chain(self):
        llm = self.llm
        prompt = hub.pull("answer_question")
        return prompt | llm | StrOutputParser()
    

    def _setup_cite_sources_chain(self):
        llm = self.llm
        llm_with_tools = llm.bind_tools([CitedSources])
        prompt = hub.pull("cite_sources")
        return prompt | llm_with_tools | PydanticToolsParser(tools=[CitedSources])
    
    async def rewrite_chat_history(self, state : OverallState):
        '''
        Transform the query to procude a better question, if a chat history is present

        Agrs:
            state: GraphState


        Returns:
            state (dict): Updates question key with a re-phrased question
        '''
        question = state['question']
        chat_history = state['messages']

        # Rewrite the question

        if len(chat_history) > 0:
            self.logger.info("Rewriting question")
            better_question = await self.question_rewriter.ainvoke({"input": question, "chat_history" : chat_history})
        else:
            self.logger.info("No chat history, using original question")
            better_question = question.content

        state['documents'].clear()

        # We replace the question with a "better question" and append the current question to the list of messages.
        print('Appending question to messages')
        return {"question": better_question, "messages": question}
    

    async def generate_question_alternatives(self, state):
        '''
        Generate alternative questions to the original question
        '''
        question = state['question']
        question_list = await self.question_alternatives.ainvoke({"QUESTION": question})
        question_list = question_list[0].questions

        self.logger.info(f"Question list: {question_list}")


        question_list.append(question)
        return {"question_list": question_list}

    
    async def search_all_documents(self, state: OverallState):
        """
        We will perform a vector search for all question and return the top documents for eacht question
        """
        # Initiate the documents list
        return [Send("retrieve", {"question": q}) for q in state["question_list"]]
    
    
    async def retrieve(self, state: QuestionState):
        '''
        Retrieve documents relevant to the question

        Args:
            state: GraphState

        Returns:
            state (dict): Updates documents key with relevant documents
        '''
        question = state['question']
        documents = await self.retriever.ainvoke(question)

        self.logger.info(f"Retrieved {len(documents)} documents")

        return {"documents": documents}
    
    async def grade_document(self, state: DocumentState):
        """
        Check if a document is relevant to the search query
        """
        doc = state['document']
        question = state['question']
        grades  =  await self.retrieval_grader.ainvoke({"document": doc.page_content, "question": question})
        grade = grades[0].binary_score

        if grade == 'yes':
            return {"graded_documents": [doc]}
        
        return None
    
    async def remove_duplicates(self, state: OverallState):
        """
        Aggregates and filters retrieved documents.

        This method performs the following tasks:
        1. Logs the number of initially retrieved documents.
        2. Filters out duplicate documents.
        3. Logs the number of unique documents after filtering.
        4. Determines if a web search is needed based on the number of remaining documents.
        """
        self.logger.info("Retrieved %s documents", len(state['documents']))
        filtered_docs = self._filter_duplicate_docs(state['documents'])
        self.logger.info("Filtered down to %s unique documents", len(filtered_docs))
        state['documents'].clear()

        
        return {"documents": filtered_docs}
    

    async def check_relevance(self, state: OverallState):
        """
        Remove an irrelevant document from the list of documents
        """

        documents = state['documents'].copy()
        state['documents'].clear()

        self.logger.info(f"Checking relevance of {len(documents)} documents")

        return [Send("grade_document", {"document": d, "question": state["question"]}) for d in documents]

    

    async def decide_web_search(self, state: OverallState):
        """
        Decides whether to perform a web search based on the number of retrieved documents.
        """
        self.logger.info(f"There are {len(state["graded_documents"])} valid documents.")

        if len (state['graded_documents']) == 0:
            return "search_web"
        else:
            return "generate"
    
    async def search_web(self, state: OverallState):
        '''
        Search the web for more documents

        Args:
            state: GraphState

        Returns:
            state (dict):  Updates documents key with appended web results
        '''

        question = state['question']
        documents = state['documents']

        docs = await self.web_search_tool.ainvoke({"query": question}, k=5)
        self.logger.info(f"Web search returned {len(docs)} documents")
        for doc in docs:
            document  = Document(page_content=doc["content"], metadata={"type": "search", "url": doc["url"]})
            documents.append(document)
        #web_results = "\n".join([d["content"] for d in docs])
        #web_results = Document(page_content=web_results, metadata={"source": "search"})
        #documents.append(web_results)

        return {"graded_documents": documents}
    

    async def rerank_sources(self, state: OverallState):
        """
        If we have more then one document, call a reranker model to rerank the documents
        """
        reranked_documents = sorted(state["graded_documents"], key=lambda x: x.metadata['score'], reverse=True)
        state["graded_documents"].clear()
        state["documents"].clear()

        # Update the rank of each document
        for i, doc in enumerate(reranked_documents, start=1):
            doc.metadata['rank'] = i

        
        
        return {"graded_documents": reranked_documents, "documents" : reranked_documents}
    

    async def group_sources(self, state: OverallState):
        return None
    

    async def response(self, state: OverallState):
        question = state["question"]
        
        sources = ""
        for i, doc in enumerate(state["graded_documents"], 1):
            sources += f"{i}. {doc.page_content}\n\n"

        response = await self.answer_question_chain.ainvoke({"SOURCES": sources, "QUESTION": question})

        return {"llm_response" : response, "messages": response}
    
    async def cite_sources(self, state: OverallState):
        question = state["question"]

        sources = ""
        for i, doc in enumerate(state["graded_documents"], 1):
            sources += f"{i}. {doc.page_content}\n\nURL: {doc.metadata['url']}\n\n"

        response = await self.cite_sources_chain.ainvoke({"SOURCES": sources, "QUESTION": question})
        state["graded_documents"].clear()

        return {"cited_sources": response, "graded_documents":  state["graded_documents"]}



    def create_graph(self, checkpointer: BaseCheckpointSaver):
        """
        Creates a state graph for the workflow.

        Args:
            checkpointer (BaseCheckpointSaver): The checkpointer object used for saving checkpoints.

        Returns:
            StateGraph: The compiled state graph.
        """
        # Open the pool

        workflow = StateGraph(OverallState)
        workflow.add_node("rewrite_chat_history", self.rewrite_chat_history)  # Rewrite the question if chat history
        workflow.add_node("generate_question_alternatives", self.generate_question_alternatives)  # Generate question alternatives
        workflow.add_node("retrieve", self.retrieve)  # retrieve
        workflow.add_node("remove_duplicates", self.remove_duplicates) #remove duplicates and irrelevant documents
        workflow.add_node("grade_document", self.grade_document) #grade document
        workflow.add_node("search_web", self.search_web)  # Search the web for more documents
        workflow.add_node("rerank_sources", self.rerank_sources)  # Rerank all the sources found
        workflow.add_node("response", self.response)  # Generate the answer
        workflow.add_node("cite_sources", self.cite_sources)  # Cite the sources
        workflow.add_node("group_sources", self.group_sources)  # Final answer
        

        workflow.add_edge(START, "rewrite_chat_history")
        workflow.add_edge("rewrite_chat_history", "generate_question_alternatives")
        workflow.add_conditional_edges("generate_question_alternatives", self.search_all_documents, ["retrieve"])
        workflow.add_edge("retrieve", "remove_duplicates")
        workflow.add_conditional_edges("remove_duplicates", self.check_relevance, ["grade_document"])
        workflow.add_edge("grade_document", "rerank_sources")
        workflow.add_conditional_edges("rerank_sources", self.decide_web_search,
                                       {
                                           "search_web": "search_web",
                                           "generate": "group_sources",
                                       })
        workflow.add_edge("search_web", "response")
        workflow.add_edge("search_web","cite_sources")
        workflow.add_edge("group_sources", "response")
        workflow.add_edge("group_sources", "cite_sources")
        workflow.add_edge("cite_sources", END)
        workflow.add_edge("response", END)
        

        return workflow.compile(checkpointer=checkpointer)
    