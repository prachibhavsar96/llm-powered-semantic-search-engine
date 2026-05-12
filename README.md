# LLM-Powered Q&A Search Engine

A lightweight FastAPI backend for storing documents, generating local embeddings, and running semantic search over uploaded text.

This project is designed as a resume-quality backend system: it uses a clean API structure, PostgreSQL persistence, local machine learning embeddings, document chunking, and beginner-friendly code that is easy to extend.

## Features

- FastAPI backend with interactive Swagger docs
- Simple JWT signup/login authentication
- User-specific documents and searches
- PostgreSQL document storage with SQLAlchemy
- Local embeddings using `sentence-transformers`
- Semantic search with cosine similarity in Python
- TXT, PDF, and DOCX upload with automatic text extraction and chunking
- In-memory caching for repeated search queries
- Pydantic request and response validation
- Clean folder structure for future Q&A, ranking, and retrieval features

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Pydantic
- Sentence Transformers
- Uvicorn

## Project Architecture

The app follows a simple layered backend architecture:

```text
Client / Swagger UI
        |
        v
FastAPI routes in app/api
        |
        v
Pydantic schemas in app/schemas
        |
        v
Services in app/services
        |
        v
SQLAlchemy models and sessions
        |
        v
PostgreSQL
```

Search flow:

```text
User query
   -> generate query embedding
   -> load stored document embeddings
   -> compute cosine similarity in Python
   -> sort by score
   -> return top_k matches
```

Document upload flow:

```text
.txt file
   -> read UTF-8 text
   -> split into paragraph and sentence chunks
   -> generate embedding for each chunk
   -> store chunks in PostgreSQL
```

## Project Tree

```text
.
|-- app/
|   |-- api/
|   |   |-- document_routes.py
|   |   |-- search_routes.py
|   |-- core/
|   |   |-- config.py
|   |-- db/
|   |   |-- database.py
|   |-- models/
|   |   |-- document.py
|   |-- schemas/
|   |   |-- document.py
|   |   |-- search.py
|   |-- services/
|   |   |-- chunking_service.py
|   |   |-- embedding_service.py
|   |   |-- ranking_service.py
|   |   |-- search_cache.py
|   |-- main.py
|-- frontend/
|   |-- src/
|   |   |-- main.jsx
|   |   |-- styles.css
|   |-- index.html
|   |-- package.json
|-- .gitignore
|-- README.md
|-- requirements.txt
```

## Setup

Clone the project and create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment.

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## PostgreSQL Setup

Create a PostgreSQL database:

```text
llm_qa_search
```

Create a `.env` file in the project root:

```text
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/llm_qa_search
SECRET_KEY=replace-this-with-a-long-random-secret
GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
```

The app creates the `documents` table automatically when it starts.

## Run The App

Start the development server:

```bash
uvicorn app.main:app --reload
```

Open the interactive API docs:

```text
http://127.0.0.1:8000/docs
```

## Run The Frontend

The React frontend lives in `frontend/` and expects the backend at:

```text
http://127.0.0.1:8000
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

To enable Google sign-in, create `frontend/.env`:

```text
VITE_GOOGLE_CLIENT_ID=your-google-oauth-client-id.apps.googleusercontent.com
```

Start the Vite development server:

```bash
npm run dev
```

Open the frontend URL printed by Vite, usually:

```text
http://localhost:5173
```

## API Usage

### Sign Up

```http
POST /auth/signup
```

```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

### Log In

```http
POST /auth/login
```

```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

Example response:

```json
{
  "access_token": "jwt-token-here",
  "token_type": "bearer"
}
```

Use the token with protected endpoints:

```text
Authorization: Bearer jwt-token-here
```

### Google Login

The frontend uses Google Identity Services to get a Google ID token, then sends it to:

```http
POST /auth/google
```

The backend verifies the Google credential and returns the same JWT response shape used by normal login.

### Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "message": "LLM Q&A Search Engine backend is running"
}
```

### Create A Document

```http
POST /documents
```

Example request:

```json
{
  "title": "Caching Notes",
  "content": "Caching stores frequently used data so applications can respond faster and reduce repeated work."
}
```

Example response:

```json
{
  "id": 1,
  "title": "Caching Notes",
  "content": "Caching stores frequently used data so applications can respond faster and reduce repeated work.",
  "created_at": "2026-05-06T12:00:00"
}
```

### Upload A Document

```http
POST /documents/upload
```

Upload a `.txt`, `.pdf`, or `.docx` file using the Swagger UI at:

```text
http://127.0.0.1:8000/docs
```

The backend extracts text from the file, chunks long text, generates embeddings, and stores each chunk as a searchable document.

Uploaded documents are linked to the logged-in user.

### Get All Documents

```http
GET /documents
```

Returns only the current user's stored documents and uploaded chunks.

### Semantic Search

```http
POST /search
```

Example request:

```json
{
  "query": "How can caching improve performance?",
  "top_k": 3
}
```

Example response:

```json
{
  "results": [
    {
      "id": 1,
      "title": "Caching Notes",
      "content": "Caching stores frequently used data so applications can respond faster and reduce repeated work.",
      "created_at": "2026-05-06T12:00:00",
      "similarity_score": 0.78,
      "final_score": 0.82,
      "answer_summary": "Based on the best matching chunk, Caching stores frequently used data so applications can respond faster and reduce repeated work. This relates to your query through terms like caching, performance. The match was ranked highest with a final score of 0.82."
    }
  ],
  "answer_summary": "Caching stores frequently used data so applications can respond faster and reduce repeated work. This answer is based on matching chunks related to caching, performance.",
  "execution_time_ms": 42.15,
  "total_documents_scanned": 12,
  "cache_hit": false
}
```

## Example Search Queries

Try adding documents about APIs, databases, caching, machine learning, and web performance. Then test queries like:

```text
How does caching reduce latency?
```

```text
Why are embeddings useful for search?
```

```text
What is the role of a database session?
```

```text
How can APIs validate incoming data?
```

Semantic search can match related meaning even when the exact words are different.

## Notes

- Embeddings are stored as JSON text in PostgreSQL to keep the project simple.
- Documents and searches are scoped to the authenticated user.
- Search computes cosine similarity in Python, combines it with keyword overlap, filters duplicate chunks, and returns the strongest useful matches.
- The top search result includes a simple 2-3 sentence `answer_summary` generated from the best matching chunk, without using an LLM.
- Search responses include execution time, scanned document count, and cache status.
- The in-memory search cache resets when the server restarts.
- The first embedding request may take longer because the local model may need to load.

## Future Improvements

- Add automated tests
- Add pagination for document listing
- Add document deletion and cache invalidation
- Add a Q&A endpoint that uses top search results as context
- Add migrations with Alembic
- Add production-ready vector indexing later if needed
