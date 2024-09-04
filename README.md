![PyPI - Version](https://img.shields.io/pypi/v/searchflow) ![Website](https://img.shields.io/website?url=https%3A%2F%2Fvectrix.ai) ![GitHub License](https://img.shields.io/github/license/vectrix-ai/SearchFlow)
 ![X (formerly Twitter) Follow](https://img.shields.io/twitter/follow/bselleslagh) ![Docker Image Version (tag)](https://img.shields.io/docker/v/bselleslagh/searchflow/latest)



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



## Usage

Install SearchFlow via pip:
```bash
pip install searchflow
```

### Quickstart
1. **Initialize the Database**

```python
from searchflow.db.postgresql import DB
db = DB()
db.create_project(project_name="example_project")
```

2. **Create a project**

```python
db.create_project(project_name="example_project")
```

3. **Import Data from a URL**

```python
from searchflow.importers import WebScraper
scraper = WebScraper(project_name='MyProject', db=db)
scraper.full_import("https://example.com", max_pages=100)
````

4. ** Upload a file to the project **

```python
from searchflow.importers import Files
with open("path/to/your/file.pdf", "rb") as f:
bytes_data = f.read()
files = Files()
files.upload_file(
document_data=[(bytes_data, "file.pdf")],
project_name="MyProject",
inference_type="local"
)
```

5. **List Files in a Project**

```python
files.list_files(project_name="MyProject")
```

6. **Remove a File from a Project**

```python
files.remove_file(project_name="MyProject", file_name="file.pdf")
```

### Question Answering



### Vector Search
To perform a similarity search:

```python
from searchflow.db.postgresql import DB
db = DB()
results = db.similarity_search(project_name="example_project", query="example query"
```