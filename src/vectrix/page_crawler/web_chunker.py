from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectrix.page_crawler.models.site_pages import PageData
from typing import List
import logging

class Webchunker:
    def __init__(self, pages: List[PageData]):
            """
            Initializes a WebChunker object.

            Args:
                pages (List[PageData]): A list of PageData objects representing the pages to be processed.

            Returns:
                None
            """
            self.pages = pages
            self.logger = logging.getLogger(__name__)
            self.logger.info(f"Webchunker initialized with {len(self.pages)} pages")
        

    def __extract_metadata(self) -> list:
        '''
        This function will extract the metdata extracted from the pages by the Trafilatura library
        '''
        keys =  ['title', 'hostname', 'image', 'source', 'source_hostname', 'excerpt']
        metadata = []

        # Create a list dictionaries of objects with only these keys
        for page in self.pages:
            metadata.append({key: getattr(page, key) for key in keys})

        return metadata

    def chunk_content(self, chunk_size: int = 1000, chunk_overlap: int = 0) -> list:
            """
            Chunk the content of the pages into smaller chunks.

            Args:
                chunk_size (int): The maximum size of each chunk in characters. Defaults to 1000.

            Returns:
                list: A list of chunks containing the content of the pages.
            """
            text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            model_name="gpt-4",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            )
            #metadatas = self.__extract_metadata()
            metadatas = [page.metadata for page in self.pages]
            content = [' '.join(page.content['raw_text'].split()) for page in self.pages]

            chunks = text_splitter.create_documents(content, metadatas=metadatas)

            self.logger.info(f"Content chunked into {len(chunks)} chunks")
            return chunks
