import datetime
import json
import warnings
from typing import List, Generator
from urllib.parse import urlparse

import validators
from bs4 import BeautifulSoup
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_core.documents import Document
from trafilatura import extract as trafilatura_extract

from vectrix import setup_logger

class WebCrawler:
    """
    A class for crawling websites and extracting content and links.

    Attributes:
        url (str): The URL of the website to crawl.
        max_pages (int): The maximum number of pages to crawl.
        check_query_strings (bool): Flag to check query strings in URLs.
        startswith (str): String that each URL should start with.
        site_name (str): The name of the site being crawled.
        logger: Logger instance for the class.
    """

    def __init__(self, url: str, max_pages: int = 1000, check_query_strings: bool = False, startswith: str = None):
        self.logger = setup_logger()
        self.url = url
        self.max_pages = max_pages
        self.check_query_strings = check_query_strings
        self.startswith = startswith
        self.site_name = url.split("//")[1].split("/")[0].replace("www.", "")
        warnings.filterwarnings('ignore', category=ResourceWarning)
        self.visited_links = set()  # Add this line to initialize visited_links

    @staticmethod
    def is_valid_url(url_string: str) -> bool:
        """Check if a URL is valid."""
        if "slide-template" in url_string.lower():
            return False
        return validators.url(url_string) or False

    @staticmethod
    def prepend_url(base_url: str, link: str) -> str:
        """Prepend base URL to a link if it starts with '/'."""
        return base_url + link if link.startswith('/') else link

    @staticmethod
    def strip_query_string(url: str) -> str:
        """Remove query string from URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def extract_site_urls(self, html: str) -> List[str]:
        """Extract URLs from HTML content of the same domain."""
        soup = BeautifulSoup(html, "html.parser")
        links = [link.get("href") for link in soup.find_all("a") if link.get("href")]
        
        links = [link for link in links if len(link) > 1 and not link.startswith("mailto") and '.mp4' not in link]
        links = [self.prepend_url(self.url, link) for link in links]
        links = [self.url + link if not link.startswith("http") else link for link in links]
        links = [link for link in links if self.site_name in link]
        links = [link for link in links if self.is_valid_url(link)]
        links = [link.split("#")[0] for link in links]
        
        return list(set(links))

    def extract(self) -> Generator[dict, None, List[Document]]:
        self.logger.info(f"Starting extraction for site: {self.site_name}")
        processed_pages = []

        loader = AsyncHtmlLoader(self.url)
        index_page = loader.load()
        self.visited_links.add(self.url)  # Use self.visited_links

        links = self.extract_site_urls(index_page[0].page_content)
        yield {"status": "Started", "pages_scraped": 0, "total_links": len(links)}

        while links:
            if self.startswith:
                links = [link for link in links if link.startswith(self.startswith)]
            
            self.logger.info(f"Visiting links: {links}")
            other_pages = AsyncHtmlLoader(links, ignore_load_errors=True)
            
            try:
                docs = other_pages.load()
            except Exception as e:
                self.logger.error(f"Error loading page: {e}")
                yield {"status": "Error", "message": str(e)}
                continue

            processed_pages.extend(docs)
            if len(processed_pages) > self.max_pages:
                self.logger.info("Maximum number of pages reached")
                yield {"status": "Max pages reached", "pages_scraped": len(processed_pages)}
                break

            # Update visited_links with the actual URLs loaded
            self.visited_links.update(doc.metadata["source"] for doc in docs)
            self.logger.info(f"Pages processed: {len(processed_pages)}")

            new_links = []
            for doc in docs:
                new_links.extend(self.extract_site_urls(doc.page_content))

            links = [link for link in new_links if link not in self.visited_links]
            self.logger.info(f"Links to visit: {len(links)}")
            yield {"status": "In progress", "pages_scraped": len(processed_pages), "links_remaining": len(links)}

        processed_pages.extend(index_page)

        docs_transformed = self._transform_documents(processed_pages)
        self.logger.info(f"SCRAPING FINISHED: Pages extracted {len(docs_transformed)}")
        yield {"status": "Finished", "pages_scraped": len(docs_transformed)}
        yield docs_transformed

    def _transform_documents(self, processed_pages: List[Document]) -> List[Document]:
        """Transform processed pages into final Document format."""
        docs_transformed = []
        for doc in processed_pages:
            try:
                extracted_content = json.loads(trafilatura_extract(
                    doc.page_content, 
                    output_format="json", 
                    include_comments=False
                ))
                transformed_doc = Document(
                    page_content=extracted_content["text"],
                    metadata={
                        "url": doc.metadata["source"],
                        "title": doc.metadata["title"],
                        "description": doc.metadata.get("description", ""),
                        "language": doc.metadata["language"],
                        "extraction_ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "source_type": "webscrape",
                        "source_format": "HTML"
                    }
                )
                docs_transformed.append(transformed_doc)
            except Exception as e:
                self.logger.error(f"Error transforming document: {e}")

        return docs_transformed