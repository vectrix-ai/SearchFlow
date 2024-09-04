import json
from trafilatura import extract
from langchain_core.documents import Document
from searchflow import logger, DB
from searchflow.extract import ExtractMetaData, ExtractionObject


class ChromeImporter:
    def __init__(self, project_name: str, db: DB):
        self.project_name = project_name
        self.logging = logger.setup_logger(name="ChromeImporter")
        self.db = db
        self.extractor = ExtractMetaData()

    def add_web_page(self, html_data: str, url: str):
        content = extract(html_data, output_format='json', with_metadata=True)
        if content:
            content = json.loads(content)

        else:
            self.logging.error(f"Error processing HTML content: {content}")
            return
        
        extraction_object = ExtractionObject(
            title=content['title'],
            content=content['raw_text'],
            url=url,
            project_name=self.project_name,
            file_type="webpage",
            source="chrome_extension",
            filename=content['title']
        )

        document = self.extractor.extract([extraction_object])

        try:
            self.db.add_documents(document, project_name=self.project_name)
        except Exception as e:
            self.logging.error(f"Error adding document to database: {e}")

        

