import uuid
from langchain_openai import ChatOpenAI, OpenAI
from langchain_anthropic import ChatAnthropic
from langchain_cohere.rerank import CohereRerank
from langchain import hub
from langchain_core.output_parsers import PydanticToolsParser, JsonOutputParser, StrOutputParser
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, SystemMessage, AIMessage, HumanMessage
from langchain.prompts.prompt import PromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain_ollama.chat_models import ChatOllama
from typing import List, Sequence
from langgraph.constants import Send
from langgraph.prebuilt import create_react_agent
from searchflow import logger
from searchflow.graphs.utils.state import OverallState, Intent, QuestionList, QuestionState, CitedSources
from searchflow.db import DB
from searchflow.graphs.utils.prompts import Prompts

logger = logger.setup_logger(name="LangGraph", level="INFO")
db = DB()

def _setup_intent_detection():
    prompt = hub.pull("vectrix/intent_detection")
    llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620")
    llm_with_tools = llm.bind_tools(tools=[Intent])
    return prompt | llm_with_tools

def _setup_question_detection():
    prompt = hub.pull("vectrix/split_questions")
    llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620")
    llm_with_tools = llm.bind_tools(tools=[QuestionList])
    return prompt | llm_with_tools

def _filter_duplicate_docs(documents : List[Document]) -> List[Document]:
    seen_uuids = set()
    unique_documents = []
    for doc in documents:
        uuid = doc.metadata.get('uuid')
        if uuid not in seen_uuids:
            seen_uuids.add(uuid)
            unique_documents.append(doc)
    return unique_documents


def _rerank_docs(documents : Sequence[Document], question: str) -> Sequence[Document]:
    reranker = CohereRerank(model="rerank-multilingual-v3.0")
    reranked_docs = reranker.rerank(documents, query=question)
    print(reranked_docs)
    return reranked_docs

def _rag_answer_chain():
        llm = ChatAnthropic(model_name="claude-3-5-sonnet-20240620", temperature=0)
        prompt_template = hub.pull("answer_question")

        return prompt_template | llm | StrOutputParser()

def _setup_cite_sources_chain():
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        llm_with_tools = llm.bind_tools([CitedSources])
        prompt = hub.pull("cite_sources")
        return prompt | llm_with_tools | PydanticToolsParser(tools=[CitedSources])

def _setup_sql_agent_chain():
    llm = OpenAI(streaming=True)
    db = DB()
    db = SQLDatabase(engine=db.engine)
    prompt_template = Prompts.sql_agent_prompt

    PROMPT = PromptTemplate(
        input_variables=["input", "dialect"], template=prompt_template
    )

def _question_rewriter_chain():
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = hub.pull("vectrix/question_rewriter")
    return prompt | llm | StrOutputParser()


def _setup_hallucination_grader():
    prompt = hub.pull("vectrix/hallucination_prompt")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return prompt | llm

async def detect_intent(state :OverallState, config):
    messages = state["messages"]
    question = messages[-1].content
    # Select all messages except the last one
    chat_history = messages[:-1]
    intent_detection = _setup_intent_detection()
    response = await intent_detection.ainvoke({"chat_history": chat_history, "question": question})
    logger.info(f"Intent detection response: {response['intent']}")
    return {"intent": response['intent']}

async def decide_answering_path(state :OverallState, config):
    print(state)
    if state["intent"] == "greeting":
        logger.info("Greeting detected")
        return "greeting"
    elif state["intent"] == "specific_question":
        return "specific_question"
    elif state["intent"] == "metadata_query":
        return "metadata_query"
    elif state["intent"] == "follow_up_question":
        return "follow_up_question"
    else:
        return "end"
    
async def split_question_list(state: OverallState, config):
    split_questions = _setup_question_detection()
    question = state['messages'][-1].content

    questions = await split_questions.ainvoke({"QUESTION": question})
    logger.info("Question was split into %s parts", len(questions))
    return {"question_list": questions}

async def llm_answer(state :OverallState, config):
    messages = state["messages"]
    llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")
    response = await llm.ainvoke(messages)
    response = AIMessage(content=response.content)
    return {"messages": response}

async def retrieve(state: QuestionState, config):
    '''
    Retrieve documents relevant to the question

    Args:
        state: GraphState

    Returns:
        state (dict): Updates documents key with relevant documents
    '''
    question = state['question']
    project_name = config.get('configurable', {}).get('project_name')
    results = await db.asimilarity_search(question=question, project_name=project_name)
    documents = []

    # Add the second element of the tuple (score) to the document metadata
    if results is not None:
        for doc in results:
            try: 
                doc[0].metadata['score'] = doc[1]
                documents.append(doc[0])
            except:
                print(doc)

    # Docs scored above 0.5 ? (boolean)
    docs_above_threshold = [doc for doc in documents if doc.metadata.get('score', 0) > 0.5]

    logger.info(f"Retrieved {len(documents)} documents from vector search")

    internet_search = config.get('configurable', {}).get('internet_search', False)

    # Search the internet if asked
    if internet_search and len(docs_above_threshold) == 0:
        web_search_tool = TavilySearchResults()
        docs = await web_search_tool.ainvoke({"query": question}, max_results=3)
        logger.info(f"Web search returned {len(docs)} documents")
        for doc in docs:
            document  = Document(
                page_content=doc["content"], 
                metadata={
                    "type": "search", 
                    "url": doc["url"],
                    "uuid": str(uuid.uuid4()),
                    "source": "web_search"
                    })
            documents.append(document)
    
    reranked_results = _rerank_docs(documents, question)
    doc_map = {i: doc for i, doc in enumerate(documents)}

    filtered_docs    = []

    for result in reranked_results:
        if result['relevance_score'] > 0.7:
            doc = doc_map[result['index']]
            doc.metadata['relevance_score'] = result['relevance_score']
            filtered_docs.append(doc)

    return {"documents": filtered_docs}


async def retrieve_documents(state: OverallState, config):
        """
        We will perform a vector search for all question and return the top documents for eacht question
        """
        # Initiate the documents list
        logger.info("Retrieving documents, for the following questions: %s", state["question_list"]['questions'])
        return [Send("retrieve", {"question": q}) for q in state["question_list"]['questions']]

async def transform_docs(state: OverallState, config):


    documents = state["documents"]
    if len(documents) == 0:
        return {"documents": []}
    
    filtered_docs = _filter_duplicate_docs(documents)

    state['documents'].clear()
    return {"documents": filtered_docs}



async def rag_answer(state: OverallState, config):
    question = state["messages"][-1].content
    
    sources = ""
    for i, doc in enumerate(state["documents"], 1):
        sources += f"{i}. {doc.page_content}\n\n"

    final_answer_chain = _rag_answer_chain()

    response = await final_answer_chain.ainvoke({"SOURCES": sources, "QUESTION": question})
    response = AIMessage(content=response)

    return {"temporary_answer": response}


async def cite_sources(state: OverallState, config):
        question = state["messages"][-1].content

        sources = ""

        if len(state["documents"]) == 0:
            logger.error('Unable to answer, no sources found')
            return {"cited_sources": ""}
        
        for i, doc in enumerate(state["documents"], 1):
            source = doc.metadata.get('source', 'Unknown')
            url = doc.metadata.get('url', 'No URL provided')
            sources += f"{i}. {doc.page_content}\n\nURL: {url}\nSOURCE: {source}\n"

        cite_sources_chain = _setup_cite_sources_chain()

        response = await cite_sources_chain.ainvoke({"SOURCES": sources, "QUESTION": question})

        return {"cited_sources": response}

async def hallucination_grader(state: OverallState, config):
    answer = state["temporary_answer"]
    documents = state["documents"]
    hallucination_grader = _setup_hallucination_grader()
    response = await hallucination_grader.ainvoke({"documents": documents, "generation": answer})
    grade = response["binary_score"]

    if grade == True:
        logger.info("Generation is grounded in facts")
        return "no_hallucinations"
    elif grade == False:
        logger.info("Generation is hallucinated")
        return "hallucinations"
    else:
        logger.info("Unable to grade hallucinations")
        return "no_hallucinations"
    
async def rewrite_question(state: OverallState, config):
    question_rewriter = _question_rewriter_chain()
    question = state["messages"][-1].content
    rewritten_question = await question_rewriter.ainvoke({"question": question})
    return {"messages": rewritten_question}

async def final_answer(state: OverallState, config):
    final_answer = state["temporary_answer"]
    return {"messages": final_answer}


async def sql_agent(state: OverallState, config):
    chain = _setup_sql_agent_chain()
        # Try this chain up to 3 times in case of error
    for _ in range(3):
        try:
            result = await chain.arun(state["messages"][-1].content)
            result = AIMessage(result)
            return {"messages": result}
        except Exception as e:
            logger.error(f"Error in SQL agent: {e}")

async def rewrite_last_message(state: OverallState, config):
    prompt = hub.pull("rewrite_answer")
    question = state["messages"][-2].content
    answer = state["messages"][-1].content
    llm = ChatOpenAI(temperature=0, model="gpt-4o")
    chain = prompt | llm
    rewritten_message = await chain.ainvoke({"question": question, "answer": answer})
    rewritten_message = AIMessage(rewritten_message.content)
    return {"messages": rewritten_message}
