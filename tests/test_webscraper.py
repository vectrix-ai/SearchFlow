from dotenv import load_dotenv
load_dotenv()

from vectrix.importers import WebScraper
from vectrix.db import DB

def test_webscraper_real():
    # Create a WebScraper instance with a test project
    project_name = "unit_tests"
    scraper = WebScraper(project_name=project_name)
    db = DB()

    try:
        db.create_project(name=project_name, description="Auto generated unit test project")
        # Get all links from example.com
        all_links = scraper.get_all_links("https://example.com/")

        # Ensure we got at least one link (the homepage)
        assert len(all_links) >= 1
        assert "https://example.com/" in all_links

        # Download the pages
        scraper.download_pages(all_links, project_name=project_name)

        # Check if the pages were actually downloaded
        downloaded_urls = db.list_scraped_urls()

        assert len(downloaded_urls) >= 1
        assert "https://example.com/" in downloaded_urls

        # You can add more assertions here to check the content of the downloaded pages
        documents = db.list_scraped_urls()
        # Check that example.com is in the list
        assert "https://example.com/" in documents
        
        # Downlaod the pages
        scraper.download_pages(documents, project_name=project_name)

    finally:
        # Clean up: remove the test project
        db.remove_project(project_name)