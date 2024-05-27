# PAGINX

![GitHub License](https://img.shields.io/github/license/vectrix-ai/paginx) ![PyPI - Version](https://img.shields.io/pypi/v/paginx) ![GitHub Tag](https://img.shields.io/github/v/tag/vectrix-ai/paginx)

 Paginx is an innovative Python-based project that leverages the power of Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) to provide intelligent question-answering capabilities for any given website. By simply entering a website URL, users can interact with an AI assistant that can answer questions and provide insights based on the content of the website.

## Setting Up a PostgreSQL instance with the pgvector Extension
To store the uploaded data for later retrieval (for example during RAG), you need to set up a PostgreSQL database with the pgvector extension enabled. This chapter guides you through the steps to install PostgreSQL, enable the pgvector extension, create a new database, and store the connection string as a URL. Alternatively, you can use hosted PostgreSQL instances provided by many cloud providers.

### 1. Install PostgreSQL and pgvector Extension
**Using Docker**
1.	Pull the PostgreSQL image with pgvector:
```sh
docker pull ankane/pgvector
```

2.	Run the PostgreSQL container with the pgvector extension enabled:
```sh
docker run -d --name paginx -e POSTGRES_PASSWORD=mysecretpassword -p 5432:5432 -e PG_EXTENSIONS="pgvector" ankane/pgvector
```

**Manual Installation**

If you prefer to install PostgreSQL and pgvector manually, please follow the instructions provided in the official documentation:

- [PostgreSQL Installation](https://www.postgresql.org/download/)
- [pgvector Installation](https://github.com/ankane/pgvector)

### 2. Create a New Database
Once you have PostgreSQL running with pgvector enabled, you need to create a new database for our application. You can do this by connecting to your PostgreSQL instance and executing the following SQL commands


Create a new database named `paginx` (you can choose a different name if you prefer):
```sql
CREATE DATABASE paginx;
```

Connect to the `paginx` database:
```sql
\c paginx;
```

Enable the pgvector extension for the `paginx` database:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Store the Connection String
After creating the database, you need to store the connection string as an enviroment variable named ```database_url```. This connection string will be used by paginx to connect to the database.


The envrioment variable can be set using the following command:
```sh
export database_url="postgresql://postgres:mysecretpassword@localhost/paginx"
```

### 4. Using a Hosted PostgreSQL Instance
If you prefer to use a hosted PostgreSQL instance, you can create a new database and store the connection string as a URL. Make sure to enable the pgvector extension for the hosted database.




