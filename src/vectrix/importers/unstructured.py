import os
import logging
from typing import List
from unstructured.partition.auto import partition
from unstructured.chunking.basic import chunk_elements
from unstructured.cleaners.core import clean
from vectrix.models.documents import VectorDocument, FileObject

class Unstructured:
    """
    The class provides methods to handle different file formats, extract their content,
    organize the information into a structured format, and divide it into smaller,
    manageable chunks suitable for efficient vector search operations.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Unstructured class initialized.")

    def process_files(self, documents: List[FileObject], chunk_size: int = 1000) -> List[VectorDocument]:
        """
        Read all files in a documents and process them using the Unstructured library.
        Returns a list of VectorDocument objects.
        """
        document_chunks = []

        self.logger.info("Processing %s documents.", len(documents))

        for document in documents:
            # Check if the file exists
            if not os.path.isfile(document.file_path):
                self.logger.error("The file %s does not exist.", document.file_path)
            
            try:
                # Use Unstructured to partition the document
                elements = partition(filename=document.file_path)
                chunks = chunk_elements(elements, max_characters=chunk_size)
                
                # Create VectorDocument objects for each chunk
                for i, chunk in enumerate(chunks):
                    text = chunk.text
                    document_chunk = VectorDocument(
                        title=document.file_name,
                        url=document.url if document.url else "",
                        content=text,
                        type=document.file_type
                    )
                    document_chunks.append(document_chunk)

            except Exception as e:
                self.logger.error("Error processing file %s: %s", document.file_path, str(e))

        return document_chunks