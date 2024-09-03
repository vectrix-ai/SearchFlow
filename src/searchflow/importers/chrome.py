import json
from trafilatura import extract
from langchain_core.documents import Document
from searchflow import logger, DB
#from searchflow.importers import ExtractionObject, ExtractMetaData


class ChromeImporter:
    def __init__(self, project_name: str, db: DB):
        self.project_name = project_name
        self.logging = logger.setup_logger(name="ChromeImporter")
        self.db = db

    def add_web_page(self, html_data: str, url: str):
        content = extract(html_data, output_format='json', with_metadata=True)
        if content:
            content = json.loads(content)

        else:
            self.logging.error(f"Error processing HTML content: {content}")
            return

        document = Document(
            page_content=content['raw_text'],
            metadata={
                "source_type": "chrome_extension",
                "source_format": "html",
                "url": url,
                "language": content['language'],
                "title": content['title']
            }
        )

        try:
            self.db.add_documents([document], project_name=self.project_name)
        except Exception as e:
            self.logging.error(f"Error adding document to database: {e}")

        

