# Private ChatGPT

Private ChatGPT is a document-grounded AI assistant built with Python. It lets users create lightweight local workspaces, upload documents, ask questions about their files, and continue multiple conversations with persistent chat history.

The project is designed as a portfolio and learning application demonstrating retrieval-augmented generation (RAG), local embeddings, vector search, document processing, feedback collection, and a browser-based AI workspace.

> The user/workspace system is not authentication. It is a local user-selection mechanism for separating application data during development.

## Features

- Create and switch between lightweight local users
- Remember the last active user in the browser
- Keep documents, chats, messages, and feedback scoped to a user and workspace
- Upload PDF, DOCX, TXT, Markdown, PNG, JPG, and JPEG files
- Extract text locally from supported documents
- Use optional local OCR for image files
- Split documents into overlapping text chunks
- Generate local embeddings with Sentence Transformers
- Search document chunks with FAISS, with a NumPy fallback
- Ask document-grounded questions through OpenRouter
- Display source citations with answers
- Maintain multiple conversations per user
- Rename and delete conversations
- Delete uploaded documents and their indexed chunks
- Collect helpful/not-helpful feedback with optional comments
- View feedback statistics
- Run lightweight retrieval evaluation
- Expose health and API documentation endpoints
- Run locally or with Docker

## Architecture

```text
Browser UI
    |
    v
FastAPI application
    |
    +--> SQLite: users, documents, chats, messages, feedback
    |
    +--> Document extraction and chunking
    |
    +--> Local embeddings
    |
    +--> FAISS/NumPy vector retrieval
    |
    +--> OpenRouter free-model routing
```

The FastAPI application serves both the API and the browser interface. The main interface is located in [`frontend/index.html`](./frontend/index.html). 

## RAG pipeline

When a user uploads a document, the application:

1. Detects the file type.
2. Extracts text locally.
3. Applies optional OCR for image files.
4. Cleans and splits the text into overlapping chunks.
5. Generates embeddings with `sentence-transformers/all-MiniLM-L6-v2`.
6. Stores chunk metadata in SQLite.
7. Stores vectors in FAISS or the NumPy fallback.

When a user asks a question:

1. The question is embedded locally.
2. The vector store searches for similar chunks.
3. Results are filtered by the active user and workspace.
4. Retrieved text is sent as context to OpenRouter.
5. The response is saved to the current conversation.
6. The UI renders the answer and source citations.

The assistant is instructed to use the retrieved context, avoid unsupported claims, and state when the answer cannot be found in the uploaded documents.

## Technology stack

| Area | Technology |
| --- | --- |
| Language | Python |
| API | FastAPI |
| Browser UI | HTML, CSS, and JavaScript served by FastAPI |
| Database | SQLite |
| Embeddings | Sentence Transformers |
| Default embedding model | `all-MiniLM-L6-v2` |
| Vector search | FAISS with NumPy fallback |
| LLM provider | OpenRouter |
| Default model route | `openrouter/free` |
| PDF extraction | pypdf |
| DOCX extraction | python-docx |
| Images | Pillow |
| Optional OCR | Tesseract through pytesseract |
| Tests | pytest |
| Containerization | Docker |

## Project structure

```text
private-chatgpt/
├── app/
│   └── backend/
│       ├── chunking.py       # Text chunking
│       ├── config.py         # Environment configuration
│       ├── db.py             # SQLite schema and data access
│       ├── evaluation.py     # Retrieval evaluation
│       ├── extract.py        # Document and image extraction
│       ├── main.py           # FastAPI application and routes
│       ├── rag.py            # Retrieval and OpenRouter generation
│       └── vector.py         # FAISS/NumPy vector operations
├── frontend/
│   └── index.html            # Main browser application
├── tests/
│   └── test_core.py          # Core regression tests
├── data/                     # Local database, uploads, and indexes
├── .env.example              # Safe environment template
├── .gitignore
├── .dockerignore
├── Dockerfile
├── render.yaml
├── requirements.txt
└── README.md
```

## Requirements

- Python 3.10 or newer
- pip
- An OpenRouter API key for generated answers
- Optional: Tesseract OCR installed and available on `PATH`
- Optional: Docker for containerized execution

## Run locally

Start the FastAPI application from the project root:

```bash
uvicorn app.backend.main:app --reload --host 127.0.0.1 --port 8000
```

Open the application at:

```text
http://localhost:8000
```

Useful URLs:

- Application: `http://localhost:8000/`
- Health check: `http://localhost:8000/health`
- Interactive API documentation: `http://localhost:8000/docs`

## Using the application

1. Create a user from the lower-left user panel.
2. Upload files using **Add documents**.
3. Wait for document processing to finish.
4. Start a new chat or select an existing conversation.
5. Ask a question about the uploaded files.
6. Review the answer and source citations.
7. Use the Documents page to inspect or delete indexed files.
8. Use Feedback & analytics to review ratings.

The browser stores the last selected user ID in local storage. This improves convenience on reload but does not provide identity verification or authentication.

## API overview

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Serve the browser application |
| GET | `/health` | Application health check |
| GET, POST | `/users` | List or create users |
| GET | `/users/{user_id}` | Get user information |
| POST | `/documents` | Upload and index a document |
| GET | `/documents` | List workspace documents |
| DELETE | `/documents/{document_id}` | Delete a document and its chunks |
| POST | `/chat` | Retrieve context and generate an answer |
| POST | `/chats` | Create a conversation |
| GET | `/chats` | List conversations |
| PATCH | `/chats/{chat_id}` | Rename a conversation |
| DELETE | `/chats/{chat_id}` | Delete a conversation |
| GET | `/chats/{chat_id}/messages` | Retrieve chat messages |
| POST | `/feedback` | Save answer feedback |
| GET | `/stats` | Return feedback statistics |
| POST | `/evaluate` | Run retrieval evaluation |

User-scoped operations require the owning user and workspace identifiers. The application checks ownership before returning or modifying resources.

## Evaluation

The evaluation module supports a small manually labelled dataset and retrieval metrics such as:

- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)

The evaluation is intended as a lightweight demonstration of retrieval quality rather than a comprehensive benchmark.

## Testing

Run the test suite from the project root:

```bash
pytest -q
```

The tests cover core chunking, extraction, evaluation, user isolation, and conversation ownership behavior.

## Docker

Build the image:

```bash
docker build -t private-chatgpt .
```

Run it locally:

```bash
docker run --rm -p 8000:8000 --env-file .env private-chatgpt
```

Then open `http://localhost:8000`.

The Docker image uses the provider-supplied `PORT` value when deployed, and defaults to port `8000` locally.

## Future scope

- Proper user authentication
- Secure login and signup
- Password or OIDC-based authentication
- Production-grade authorization
- Stronger security and access control
- Durable object storage for uploads
- Managed database persistence
- Hosted vector storage
- Background document-processing jobs
- More comprehensive RAG evaluation
- Production observability and alerting
- Rate limiting and abuse prevention