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
from langchain_community.document_loaders import SpiderLoader
from searchflow import logger
from searchflow.db import DB
from searchflow.extract.extraction import ExtractMetaData, ExtractionObject



class WebScraper:
    '''
    This class uses trafilatura as a web scraper
    '''
    def __init__(self, project_name: str, db: DB):
        self.logger = logger.setup_logger(name="WebScraper", level="WARNING")
        self.my_config = deepcopy(DEFAULT_CONFIG)
        self.my_config['DEFAULT']['SLEEP_TIME'] = '1'
        self.db = db
        self.downoad_threads = 10
        self.project_name = project_name
        self.extractor = ExtractMetaData()


    def get_all_links(self, base_url: str, max_seen_urls: int = 1000, max_known_urls: int = 100000) -> None:
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


        # Add the base url to the list of links to be indexed
        self.db.add_links_to_index(base_url=base_url, links=[base_url], project_name=self.project_name, status="To be indexed")
        to_visit, known_links = focused_crawler(base_url, max_seen_urls=1, config=self.my_config)
        self.logger.info("Starting to scrape %s links", len(known_links))
        to_visit, known_links = focused_crawler(base_url,
                                                max_seen_urls=max_seen_urls,
                                                max_known_urls=max_known_urls,
                                                todo=to_visit,
                                                known_links=known_links,
                                                config=self.my_config,
                                                )
        self.logger.info("Finished scraping %s links", len(known_links))
        self.db.remove_indexed_link(url=base_url, project_name=self.project_name)

        # Remove the base url from the list of links to be indexed
        known_links = [link for link in known_links if link != base_url]
        self.db.add_links_to_index(base_url=base_url, links=known_links, project_name=self.project_name, status="Confirm page import")
        return None
    
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
        print(f"Already downloaded {len(already_downloaded)}")

        if already_downloaded:
            to_download = [url for url in urls if url not in already_downloaded]
        else:
            to_download = urls

        print(f"To download {to_download}")

        to_download = add_to_compressed_dict(to_download)

        downloaded_objects = []
        

        while to_download.done is False:
            bufferlist, url_store = load_download_buffer(url_store=to_download, sleep_time=0)
            for url, result in buffered_downloads(bufferlist, self.downoad_threads):
                downloaded_page = extract(result, output_format='json', include_links=True, with_metadata=True, config=self.my_config)
                if downloaded_page:
                    downloaded_page = json.loads(downloaded_page)
                    downloaded_objects.append(ExtractionObject(
                        title=downloaded_page['title'],
                        content=downloaded_page['raw_text'],
                        url=url,
                        project_name=project_name,
                        file_type="webpage",
                        source="webpage",
                    ))
                else:
                    self.logger.error(f"No page found for {url}")
                    self.db.remove_by_url(url=url, project_name=project_name)
                    
        downloaded_pages = self.extractor.extract(downloaded_objects)

        try:
            self.db.add_documents(downloaded_pages, project_name=project_name)
            for url in urls:
                self.db.update_indexed_link_status(url=url, project_name=project_name, status="Indexed")
        except Exception as e:
            self.logger.error(f"Error adding documents: {e}")
            return False

        return None

    def full_import(self, url: str, max_pages: int):
        '''
        Using the Spider API we will scrape the full site and store them as a list of documents in the vector store.
        Note that is is a paid feature and an API key is needed as environment variable (SPIDER_API_KEY)

        args:
            url: The base URL to scrape
            max_pages: The maximum number of pages to scrape
        '''    
        self.logger.info("Starting full import for %s", url)
        loader = SpiderLoader(
            url=url,
            mode="crawl",
            params={'limit': max_pages, 'metadata': True}
        )
        print("Starting to load")
        data = loader.load()

        pages = []

        if data:
            for doc in data:
                pages.append(
                    ExtractionObject(
                        title=doc.metadata['title'],
                        content=doc.page_content,
                        url=doc.metadata['url'],
                        project_name=self.project_name,
                        file_type="webpage",
                        source="webpage",
                    )
                )
            try:
                pages = self.extractor.extract(pages)
                self.db.add_documents(pages, project_name=self.project_name)
                self.db.add_links_to_index(base_url=url, links=[doc.metadata['url']], project_name=self.project_name, status="Indexed")
            except:
                self.logger.error("Error extracting metadata for %s", url)
        else:
            self.logger.error("No data found for %s", url)


        


