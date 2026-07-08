# LLM-Powered Q&A Search Engine

A full-stack semantic search application that allows users to upload documents and perform intelligent search using local vector embeddings and cosine similarity.

Built with FastAPI, PostgreSQL, React, and Sentence Transformers.

## Application Preview

### Login Page

<img width="1625" height="990" alt="image" src="https://github.com/user-attachments/assets/1cc4ab00-1f75-4b4d-a9fa-b76c79f40223" />

---

### Swagger API Documentation

<img width="1882" height="1037" alt="image" src="https://github.com/user-attachments/assets/d4575ea0-7e7c-4979-bd38-c556b321dd50" />

---

### Semantic Search Results

<img width="1676" height="935" alt="image" src="https://github.com/user-attachments/assets/e0deab28-7a95-4e92-8ac5-43e14f484b1d" />


---

### Document Upload

<img width="1612" height="843" alt="image" src="https://github.com/user-attachments/assets/0cd94802-3cb3-4efe-9724-28e7c8615ece" />


---

## Features

- JWT Authentication (Login / Signup)
- Google OAuth Login
- Semantic document search using embeddings
- PDF, DOCX, and TXT upload support
- User-specific private document storage
- Cosine similarity ranking
- Search result summarization
- In-memory caching for repeated searches
- Interactive Swagger API documentation

---

## Tech Stack

### Backend
- FastAPI
- PostgreSQL
- SQLAlchemy
- Sentence Transformers
- Pydantic
- JWT Authentication

### Frontend
- React
- Vite
- Google Identity Services

---

## Project Structure

```text
app/
 ├── api/
 ├── core/
 ├── db/
 ├── models/
 ├── schemas/
 ├── services/
 └── main.py

frontend/
 ├── src/
 ├── index.html
 └── package.json
```

---

## Setup Instructions

### 1. Clone Repository

```bash
git clone https://github.com/prachibhavsar96/llm-powered-semantic-search-engine.git
cd llm-powered-semantic-search-engine
```

---

### 2. Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

#### Windows

```bash
.\venv\Scripts\Activate.ps1
```

#### macOS/Linux

```bash
source venv/bin/activate
```

---

### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Configure PostgreSQL

Create database:

```sql
CREATE DATABASE llm_search_engine;
```

Create `.env` in project root:

```env
DATABASE_URL=postgresql://postgres:your_password@127.0.0.1:5432/llm_search_engine
SECRET_KEY=your_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
```

---

### 5. Run Backend

```bash
python -m uvicorn app.main:app --reload
```

Backend runs at:

```text
http://127.0.0.1:8000
```

Swagger Docs:

```text
http://127.0.0.1:8000/docs
```

---

### 6. Setup Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env`

```env
VITE_GOOGLE_CLIENT_ID=your_google_client_id
```

Run frontend:

```bash
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

---

## Authentication APIs

### Signup

```http
POST /auth/signup
```

### Login

```http
POST /auth/login
```

### Google Login

```http
POST /auth/google
```

---

## Search Workflow

1. Upload document
2. Extract text
3. Generate embeddings
4. Store chunks in PostgreSQL
5. Perform cosine similarity search
6. Return ranked semantic matches

---

## Example Search Queries

- How does caching reduce latency?
- What are vector embeddings?
- Explain database sessions
- How does semantic search work?

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

## Contributors

- Prachi Bhavsar
- Om Shah


