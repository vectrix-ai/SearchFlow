from vectrix.page_crawler.crawler import Crawler
from vectrix.page_crawler.web_chunker import Webchunker
from vectrix.ner.extract import Extract

crawler = Crawler("https://vectrix.ai")
site_pages = crawler.extract()

chunker = Webchunker(site_pages)
chunks = chunker.chunk_content(chunk_size=100)

extractor = Extract('Replicate', 'meta/meta-llama-3-70b-instruct')
results = extractor.extract(chunks)