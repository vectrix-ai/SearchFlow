from dotenv import load_dotenv
load_dotenv()

from searchflow.importers import WebScraper
from searchflow.db import DB

def test_webscraper_real():
    # Create a WebScraper instance with a test project
    project_name = "unit_tests"
    db = DB()
    scraper = WebScraper(project_name=project_name, db=db)

    try:
        # Create a project
        db.create_project(name=project_name, description="Auto generated unit test project")
        
        '''
        # Get all links from scrape all links from the website
        scraper.get_all_links("https://vectrix.ai/")

        # Check that the status lenght is one for this website
        status = db.get_indexing_status(project_name=project_name)
        print(status)
        assert len(status) == 1
        assert status[0]['base_url'] == "https://vectrix.ai/"

        # Download the pages
        scraper.download_pages([link['url'] for link in links], project_name=project_name)

        # Check that the status is set to indexed
        status = db.get_indexing_status(project_name=project_name)
        assert len(status) == 1
        assert status[0]['url'] == "https://vectrix.ai/"
        assert status[0]['status'] == "indexed"
        '''
            
    finally:
        # Clean up: remove the test project
        db.remove_project(project_name)