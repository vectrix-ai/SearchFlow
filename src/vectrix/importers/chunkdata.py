from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


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