from paginx.llm.llm import LLM
from paginx.ner.models.entities import NERExtraction

from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
import nest_asyncio
import asyncio, uuid, logging
from tqdm import tqdm
from typing import List

class Extract:
    """
    A class used to extract Named Entity Recognition (NER) from chunks of text.

    ...

    Attributes
    ----------
    modem_provider : str
        a string representing the provider of the model
    model_name : str
        a string representing the name of the model
    model : LLM
        an instance of the LLM class
    chain : PromptTemplate
        a pipeline of operations to be performed on the input

    Methods
    -------
    process_page_content(chunk, semaphore):
        Processes a chunk of text and extracts NER from it.
    extract(chunks):
        Extracts NER from a list of chunks of text.
    """
    def __init__(self, model_provider: str, model_name: str) -> None:
        """
        Constructs all the necessary attributes for the Extract object.

        Parameters
        ----------
            model_provider : str
                The provider of the model
            model_name : str
                The name of the model
        """
        self.modem_provider = model_provider
        self.model_name = model_name
        self.model = LLM(model_provider, model_name).return_llm()

        parser = PydanticOutputParser(pydantic_object=NERExtraction)
        prompt = PromptTemplate(
            template="Answer the user query.\n{format_instructions}\n{query}\n",
            input_variables=["query"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        nest_asyncio.apply()
        self.chain = prompt | self.model | parser
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Extract initialized with model provider: {model_provider} and model name: {model_name}")

    async def process_page_content(self, chunk, semaphore):
        """
        Processes a chunk of text and extracts NER from it.

        Parameters
        ----------
            chunk : object
                The chunk of text to be processed
            semaphore : asyncio.Semaphore
                The semaphore to limit the number of concurrent tasks

        Returns
        -------
            chunk : object
                The processed chunk of text with NER metadata
        """
        async with semaphore:
            try:
                response = await self.chain.ainvoke({"query": chunk.page_content})
                chunk.metadata['uuid'] = str(uuid.uuid4())
                chunk.metadata['NER'] = response.dict()
                return chunk
            except Exception as e:
                print(f"An error occurred: {e}")
                return None  # or some other value indicating failure 


    def extract(self, chunks) -> List[NERExtraction]:
        """
        Extracts NER from a list of chunks of text.

        Parameters
        ----------
            chunks : list
                The list of chunks of text to be processed

        Returns
        -------
            list
                A list of processed chunks of text with NER metadata
        """
        async def run_extraction():
            semaphore = asyncio.Semaphore(5)  # Limit concurrency to 4
            tasks = []
            chunks_with_responses = []
            for i, chunk in enumerate(chunks):
                task = asyncio.create_task(self.process_page_content(chunk, semaphore))
                tasks.append(task)
            
            responses = []
            for i, future in tqdm(enumerate(asyncio.as_completed(tasks)), total=len(tasks), desc="Extracting entities"):
                chunk = await future
                chunks_with_responses.append(chunk)
                #print(f"Task {i+1} of {len(tasks)} completed.")
            return chunks_with_responses

        # Get the current event loop
        loop = asyncio.get_event_loop()

        # Run the main function using the current event loop
        results = loop.run_until_complete(run_extraction())

        # remove all results that are None
        self.logger.info(f"NER extraction completed for {len(results)} chunks")
        return [result for result in results if result is not None]


    




