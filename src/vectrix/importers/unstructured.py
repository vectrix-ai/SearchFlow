import os
import re
import uuid
import json
from typing import List
from langchain_core.documents import Document
from vectrix import logger
from vectrix.db import DB

class Files:
    """
    The class provides methods to handle different file formats, extract their content,
    organize the information into a structured format, and divide it into smaller,
    manageable chunks suitable for efficient vector search operations.
    """

    def __init__(self):
        self.logger = logger.setup_logger(name='Files', level="INFO")
        self.db = DB()


    def upload_file(
            self, 
            document_paths: List[str], 
            project_name: str, 
            chunk_size: int = 1000,
            inference_type: str = "local"
            ) -> None:
        """
        This method will:
        - Upload a file to the object storage
        - Parse the contents with Unstructured
        - Chunk the contents, given the chunk size parameter
        - Load the document into the database and calculate the vector representation

        Args:
            document_paths (List[str]): List of file paths to upload
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

            for document_path in document_paths:
                self.logger.info("Processing file %s of %s", idx, len(document_paths))
                if not os.path.isfile(document_path):
                    self.logger.error("The file %s does not exist.", document_path)
                    continue
                
                filename = os.path.basename(document_path)
                storage_url = self.db.add_file(filename=filename, project_name=project_name, file_path=document_path)
                self.logger.info("Uploaded %s to object storage", document_path)

                file_name = os.path.basename(document_path)
                # Remove all special characters like * [ ] etc from the file_name
                file_type = os.path.splitext(file_name)[1].replace(".", "")


                try:
                    elements = partition(filename=document_path)
                    chunks = chunk_elements(elements, max_characters=chunk_size)
                    self.logger.info("Chunked the document into %s parts", len(chunks))

                    for chunk in chunks:
                        cleaned_text = re.sub('\x00', '', chunk.text)
                        doc = Document(
                            page_content=cleaned_text,
                            metadata={
                                "url": storage_url,
                                "uuid" : str(uuid.uuid4()),
                                "title": file_name,
                                "language":"",
                                "source_type": file_type,
                                "source_format": "uploaded_file"
                            }
                            )
                        self.db.add_documents(project_name=project_name, documents=[doc])
                        
                except Exception as e:
                    self.logger.error("Error parsing file %s: %s", document_path, e)
                
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

            for document_path in document_paths:
                with open(document_path, "rb") as f:
                    data = f.read()

                req = operations.PartitionRequest(
                    partition_parameters=shared.PartitionParameters(
                        files=shared.Files(
                            content=data,
                            file_name=document_path,
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
                    self.logger.error("Error parsing file %s: %s", document_path, e)

        else:
            self.logger.error("Invalid inference type. Choose either 'cloud' or 'local'.")


            