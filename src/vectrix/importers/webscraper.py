import logging
import datetime
from urllib.parse import urlparse
import json
from typing import List
import validators
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_core.documents import Document
from bs4 import BeautifulSoup
from trafilatura import extract as trafilatura_extract

logging.basicConfig(level=logging.ERROR, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class WebCrawler:
    """
    A class used to crawl a website and extract its content and links.

    ...

    Attributes
    ----------
    url : str
        the URL of the website to crawl
    max_pages : int, optional
        the maximum number of pages to crawl (default is 1000)
    check_query_strings : bool, optional
        a flag used to check query strings in URLs (default is False)
    startswith : str, optional
        a string that each URL should start with (default is None)

    Methods
    -------
    is_valid_url(url_string: str) -> bool:
        Checks if a URL is valid.
    prepend_url(base_url, link):
        Prepends a base URL to a link if it starts with '/'.
    extract_site_urls(html: str, site_name:str, url: str) -> list:
        Extracts the URLs from the HTML content of a website.
    extract() -> list:
        Extracts the site content as Markdown and a list of links from the website.
    """
    def __init__(self, url:str, max_pages:int=1000, check_query_strings:bool=False, startswith:str=None):
        self.logger = logging.getLogger(__name__)
        self.url = url
        self.max_pages = max_pages
        self.check_query_strings = check_query_strings
        self.startswith = startswith
        self.site_name = url.split("//")[1].split("/")[0].replace("www.", "")

    @staticmethod
    def is_valid_url(url_string: str) -> bool:
        """
        Returns True if the URL is valid, False otherwise.
        """
        result = validators.url(url_string)
        # Url with the words Slide-template are not valid
        if "slide-template" in url_string.lower():
            return False
        if result:
            return result
        else:
            return False

    @staticmethod   
    def prepend_url(base_url, link):
        """
        Prepends a base URL to a link if it starts with '/'.
        """
        if link.startswith('/'):
            return base_url + link
        else:
            return link

    @staticmethod
    def strip_query_string(url):
        """
        Remove query string from url
        """
        parsed = urlparse(url)
        return parsed.scheme + "://" + parsed.netloc + parsed.path
        
    
    def extract_site_urls(self, html: str, site_name:str) -> list:
        '''
        Extract the URLs from the HTML content
        Only if the domain name is the same
        Returns a list of strings
        '''
        soup = BeautifulSoup(html, "html.parser")
        links = [link.get("href") for link in soup.find_all("a") if link.get("href") is not None]

        # Remove empty links and mailto links
        links = [link for link in links if len(link) > 1 and not link.startswith("mailto")]
        
        # Add the base URL to the links
        links = [self.prepend_url(self.url, link) for link in links]
        links = [self.url + link if not link.startswith("http") else link for link in links]
        # Remove links that are not from the same site
        links = [link for link in links if site_name in link]
        # Check fo valid URLs
        links = [link for link in links if self.is_valid_url(link)]
        # Remove everything after the # sign
        links = [link.split("#")[0] for link in links]
        # Remove duplicates
        links = list(set(links))    
        return links
    
    def extract(self) -> List[Document]:
            '''
            The input as a URL
            Returns the site content as Markdown and a list of links (from that same site)

            :return: A list of site content in Markdown format and a list of links from the same site
            :rtype: list
            '''
            self.logger.info("Starting extraction pipeline for site: %s", self.site_name)

            visited_links = []

            loader = AsyncHtmlLoader(self.url)
            index_page = loader.load()
            visited_links.append(self.url)

            html = index_page[0].page_content


            links = self.extract_site_urls(html, self.site_name)
            processed_pages = []

            while len(links) > 0 :
                self.logger.info("Visiting the following links: %s", links)
                if self.startswith:
                    links = [link for link in links if link.startswith(self.startswith)]
                other_pages = AsyncHtmlLoader(links, ignore_load_errors=True)
                try:
                    docs = other_pages.load()
                except Exception as e:
                    self.logger.error("Error loading the page: %s", e)
                processed_pages.extend(docs)
                if len(processed_pages) > self.max_pages:
                    self.logger.info("Maximum number of pages reached")
                    break
                visited_links.extend(self.strip_query_string(link) for link in links)
                self.logger.info("Number of pages processed: %d", len(processed_pages))
                for doc in docs:
                    # Extracting links from 
                    links.extend(self.extract_site_urls(doc.page_content, self.site_name))

                # Remove visited links
                links = [link for link in links if self.strip_query_string(link) not in visited_links]

                self.logger.info("Number of links to visit: %d", len(links))

            processed_pages.extend(index_page)

            self.logger.info("Download finished. Extracting content from the pages.")
            # Apply the excract method to each element of the list


            #docs = [Document(page_content=doc)]


            docs_transformed = [{"metadata": doc.metadata,
                                 "content": json.loads(trafilatura_extract(doc.page_content, output_format="json", include_comments=False))} for doc in processed_pages]
            

            

            docs_transformed = [Document(page_content=doc["content"]["text"],
                                         metadata={
                                             "url": doc["metadata"]["source"],
                                             "title": doc["metadata"]["title"],
                                             "description": doc["metadata"]["description"],
                                             "language" : doc["metadata"]["language"],
                                             "extraction_ts" : datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                             "source_type" : "webscrape",
                                             "source_format" : "HTML"
                                         }) for doc in docs_transformed]
            
            return docs_transformed