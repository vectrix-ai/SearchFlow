from paginx.page_crawler.crawler import Crawler
from paginx.page_crawler.web_chunker import Webchunker

crawler = Crawler("https://vectrix.ai")
site_pages = crawler.extract()


chunker = Webchunker(site_pages)
chunks = chunker.chunk_content(chunk_size=100)