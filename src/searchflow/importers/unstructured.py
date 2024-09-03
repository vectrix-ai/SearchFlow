import os
import re
import uuid
import json
from typing import List
from langchain_core.documents import Document
from searchflow import logger
from searchflow.db import DB
from searchflow.importers.extraction import ExtractMetaData, ExtractionObject

class Files:
    """
    The class provides methods to handle different file formats, extract their content,
    organize the information into a structured format, and divide it into smaller,
    manageable chunks suitable for efficient vector search operations.
    """

    def __init__(self):
        self.logger = logger.setup_logger(name='Files', level="INFO")
        self.db = DB()
        self.extractor = ExtractMetaData()


    def upload_file(
            self, 
            document_data: List[tuple],  # List of tuples: (bytes_data, filename)
            project_name: str, 
            chunk_size: int = 1000,
            inference_type: str = "local"
            ) -> None:
        """
        This method will:
        - Upload file data to the object storage
        - Parse the contents with Unstructured
        - Chunk the contents, given the chunk size parameter
        - Load the document into the database and calculate the vector representation

        Args:
            document_data (List[tuple]): List of tuples containing (bytes_data, filename)
            project_name (str): The name of the project to associate the document with
            chunk_size (int): The size of the chunks to divide the document into
            inference_type (str): cloud or local

        Returns:
            None
        """
        idx = 1

        if inference_type == "local":
            # Process all the files on device
            self.logger.info("Processing files locally")

            from unstructured.partition.auto import partition
            from unstructured.chunking.basic import chunk_elements
            import io

            for bytes_data, filename in document_data:
                self.logger.info("Processing file %s of %s", idx, len(document_data))
                
                # Create a temporary file-like object
                file_obj = io.BytesIO(bytes_data)
                
                storage_url = self.db.add_file(document_data=(bytes_data, filename), project_name=project_name)
                self.logger.info("Uploaded %s to object storage", filename)

                file_type = os.path.splitext(filename)[1].replace(".", "")

                try:
                    # Use partition with file-like object instead of filename
                    elements = partition(file=file_obj)
                    chunks = chunk_elements(elements, max_characters=9999999999)
                    self.logger.info("Chunked the document into %s parts", len(chunks))

                    docs = []

                    for chunk in chunks:
                        cleaned_text = re.sub('\x00', '', chunk.text)
                        doc = ExtractionObject(
                            title=filename,
                            content=cleaned_text,
                            url=storage_url,
                            project_name=project_name,
                            file_type=file_type,
                            source="uploaded_file",
                            filename=filename
                        )
                        docs.append(doc)
                    docs = self.extractor.extract(docs)
                    self.db.add_documents(project_name=project_name, documents=docs)
                        
                except Exception as e:
                    self.logger.error("Error parsing file %s: %s", filename, e)
                
                idx += 1

        elif inference_type == "cloud":
            self.logger.info("Processing files using the unstructured API")
            # Process files using the unstructured API
            import unstructured_client
            from unstructured_client.models import operations, shared

            client = unstructured_client.UnstructuredClient(
                api_key_auth=os.getenv("UNSTRUCTURED_API_KEY"),
                server_url=os.getenv("UNSTRUCTURED_API_URL"),
            )

            for bytes_data, filename in document_data:
                req = operations.PartitionRequest(
                    partition_parameters=shared.PartitionParameters(
                        files=shared.Files(
                            content=bytes_data,
                            file_name=filename,
                        ),
                        strategy=shared.Strategy.AUTO,
                        split_pdf_page=True,
                        split_pdf_allow_failed=True,
                        split_pdf_concurrency_level=15
                    ),
                )

                try:
                    res = client.general.partition(request=req)
                    element_dicts = [element for element in res.elements]
                    json_elements = json.dumps(element_dicts, indent=2)

                    return json_elements
                except Exception as e:
                    self.logger.error("Error parsing file %s: %s", filename, e)

        else:
            self.logger.error("Invalid inference type. Choose either 'cloud' or 'local'.")


            