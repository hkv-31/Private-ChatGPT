# Private ChatGPT

A beginner-friendly local document chat application. FastAPI provides a small SQLite-backed API and a polished browser UI. Documents are extracted, chunked, embedded locally with `sentence-transformers`, and searched with a user/workspace-scoped vector store. Answers use OpenRouter when configured and include chunk citations.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.backend.main:app --reload
```

Open `http://localhost:8000`. The browser UI stores the last active user in local browser storage. The user/workspace mechanism is not authentication.

The older `streamlit_app.py` remains available as an optional prototype, but it is not required for the main application.

## Deployment preparation

The project includes a Docker deployment configuration and [`render.yaml`](./render.yaml). A free Render web service is the better fit for this prototype because it can run the complete FastAPI process and Docker image. Set `OPENROUTER_API_KEY` as a platform secret; never commit it.

Vercel can host a small FastAPI function, but it is not recommended for this application. Vercel's serverless execution model is a poor match for local SQLite, uploaded files, FAISS indexes, local embedding-model downloads, and potentially slow RAG requests. Its filesystem is not a durable database or upload store, and function timeouts can interrupt model loading or OpenRouter calls. Use Vercel only if the frontend is separated from the backend and persistence/vector storage are moved to external services.

Render's free service is suitable for a portfolio demo, but its filesystem is ephemeral and the service sleeps after inactivity. Uploaded documents and SQLite data should therefore be treated as demo data, not durable production storage. For a persistent deployment, use an external database/object store and a hosted vector store later.

## API

Endpoints include `GET/POST /users`, `GET/DELETE /documents`, `POST /chat`, `POST/GET/DELETE /chats`, `GET /chats/{id}/messages`, `POST /feedback`, `GET /stats`, and `POST /evaluate`. Every resource lookup requires the owning user and workspace where applicable; cross-user access returns 404. The OpenAPI page is at `/docs`.

## Free-tier constraints and privacy

The default model is OpenRouter's `openrouter/free` router, which selects an available free model. Free models are subject to provider quotas, rate limits, availability, and context limits. Without an API key, local extraction/search still works and the API returns retrieved context rather than calling a provider. Embedding models and FAISS are downloaded/loaded locally and can use substantial RAM/disk (a NumPy cosine fallback is used if FAISS cannot load). OCR additionally requires the Tesseract system binary. SQLite and indexes are local; add backups and access controls before sharing.

Real authentication, authorization, multi-user identity, encryption, and production deployment are intentionally **future scope**. The user/workspace identifiers provide application-level isolation, but are not identity proof or a security boundary. Do not expose this development server publicly.

Never commit `.env` or share an OpenRouter key in screenshots, chat, notebooks, or source control. If a key is exposed, revoke it in OpenRouter and create a replacement.

## Tests

```bash
pytest -q
```

`app.backend.main` does not call external APIs or load models at import time. Optional extraction/OCR and embedding dependencies degrade gracefully.
