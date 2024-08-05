from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ChunkData:
    """
    A class for processing and chunking web page content.

    This class takes a list of WebPageData objects, which represent web pages,
    and provides methods to extract metadata and chunk the content of these pages.

    Attributes:
        pages (List[WebPageData]): A list of WebPageData objects representing the web pages.
        logger (logging.Logger): A logger object for logging information and errors.

    Methods:
        __extract_metadata(): Extracts metadata from the pages.
        chunk_content(chunk_size: int = 1000, chunk_overlap: int = 0): Chunks the content of the pages.
    """

    def chunk_content(documents: List[Document], chunk_size: int = 1000, chunk_overlap: int = 0) -> List[Document]:
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
        
        metadatas = [doc.metadata for doc in documents]
        content = [' '.join(doc.page_content.split()) for doc in documents]

        chunks = text_splitter.create_documents(content, metadatas=metadatas)
        return chunks