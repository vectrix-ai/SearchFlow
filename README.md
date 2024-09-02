# SearchFlow

SearchFlow is an assistant designed to help you index webpages into structured datasets. It leverages various tools and models to scrape, process, and store web content efficiently.

## Features

- **Web Scraping**: Uses `trafilatura` for focused crawling and web scraping.
- **Document Processing**: Supports chunking and processing of various document types.
- **Database Management**: Manages projects, documents, and prompts using PostgreSQL.
- **Vector Search**: Utilizes vector search for document retrieval.
- **LLM Integration**: Integrates with language models for question answering and document grading.

## Installation

To set up the development environment, use the provided `Dockerfile` and `.devcontainer/devcontainer.json` for a consistent development setup.

### Prerequisites

- Docker
- Python 3.11 or higher

### Steps

1. **Clone the repository**:
    ```sh
    git clone https://github.com/yourusername/searchflow.git
    cd searchflow
    ```

2. **Build the Docker container**:
    ```sh
    docker build -t searchflow .
    ```

3. **Run the Docker container**:
    ```sh
    docker run -it -p 8501:8501 searchflow
    ```

## Usage

### Web Scraping

To scrape a website and index the links:

```python
from searchflow.importers.webscraper import WebScraper
scraper = WebScraper(project_name="example_project")
scraper.get_all_links(base_url="https://example.com")
```

### Document Processing

To upload and process files:

```python
from searchflow.importers.file_importer import FileImporter
files = Files()
files.upload_file(document_data=[(b"file_content", "example.pdf")], project_name="example_project")
```

### Vector Search
To perform a similarity search:

```python
from searchflow.db.postgresql import DB
db = DB()
results = db.similarity_search(project_name="example_project", query="example query"
```

