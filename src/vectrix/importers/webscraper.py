import os
from copy import deepcopy
import hashlib
import json
from typing import List
from urllib.parse import urlparse
from trafilatura.spider import focused_crawler
from trafilatura.settings import DEFAULT_CONFIG
from trafilatura import extract
from trafilatura.downloads import add_to_compressed_dict, load_download_buffer, buffered_downloads
from langchain_core.documents import Document
from vectrix import logger
from vectrix.db import DB
from vectrix.importers.chunkdata import chunk_content

class WebScraper:
    '''
    This class uses trafilatura as a web scraper
    '''
    def __init__(self, project_name: str):
        self.logger = logger.setup_logger(name="WebScraper", level="ERROR")
        self.my_config = deepcopy(DEFAULT_CONFIG)
        self.my_config['DEFAULT']['SLEEP_TIME'] = '1'
        self.db = DB()
        self.downoad_threads = 10
        self.project_name = project_name


    def get_all_links(self, base_url: str, max_seen_urls: int = 1000, max_known_urls: int = 100000) -> List[str]:
        '''
        Scrapes a website and returns a list of all discovered links.

        This function uses trafilatura's focused_crawler to perform a two-step crawling process:
        1. An initial crawl with max_seen_urls set to 1 to initialize the crawling process.
        2. A more extensive crawl using the provided parameters.
        Args:
            max_seen_urls (int): The maximum number of URLs to visit during the crawl. Default is 1000.
            max_known_urls (int): The maximum number of URLs to keep in memory. Default is 100000.

        Returns:
            List[str]: A list of all unique URLs discovered during the crawling process.

        Raises:
            Any exceptions raised by trafilatura's focused_crawler function.

        Note:
            This function logs the number of links at the start and end of the crawling process.
        '''
        self.db.set_scrape_status(base_url=base_url, status="Scraping links", project_name=self.project_name)
        to_visit, known_links = focused_crawler(base_url, max_seen_urls=1, config=self.my_config)
        self.logger.info("Starting to scrape %s links", len(known_links))
        to_visit, known_links = focused_crawler(base_url,
                                                max_seen_urls=max_seen_urls,
                                                max_known_urls=max_known_urls,
                                                todo=to_visit,
                                                known_links=known_links,
                                                config=self.my_config)
        self.logger.info("Finished scraping %s links", len(known_links))
        self.db.add_links_to_confirm(links=known_links, project_name=self.project_name, base_url=base_url)
        self.db.set_scrape_status(base_url=base_url, status="Confirm page import", project_name=self.project_name)
        return known_links
    
    @staticmethod
    def extract_domain(url):
        """
        Extract the domain name from a URL
        """
        return urlparse(url).netloc
    
    def download_pages(self, urls: List[str], project_name: str):
        """
        Downloads all pages from a URL and stores
        """
        already_downloaded = self.db.list_scraped_urls()

        if already_downloaded:
            to_download = [url for url in urls if url not in already_downloaded]
        else:
            to_download = urls

        to_download = add_to_compressed_dict(to_download)

        self.db.set_scrape_status(status="Importing pages", project_name=project_name)
        self.db.remove_uploaded_links(project_name=project_name)

        while to_download.done is False:
            bufferlist, url_store = load_download_buffer(url_store=to_download, sleep_time=0)
            for url, result in buffered_downloads(bufferlist, self.downoad_threads):
                downloaded_page = extract(result, output_format='json', include_links=True, with_metadata=True, config=self.my_config)
                if downloaded_page:
                    downloaded_page = json.loads(downloaded_page)
                    doc = Document(
                        page_content=downloaded_page['raw_text'],
                        metadata={
                            "title": downloaded_page['title'],
                            "url": url,
                            "language": downloaded_page['language'],
                            "source_type": "webpage",
                            "source_format": "html"
                        }
                    )

                    chunked_docs = chunk_content([doc])
                    self.db.add_documents(chunked_docs, project_name=project_name)
        self.db.set_scrape_status(status="Website indexed", project_name=project_name)
        return None


