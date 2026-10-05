import json
import logging
import asyncio
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .config import settings
from .db import Database
from .extract import extract_text
from .chunking import chunk_text
from .vector import VectorStore
from .rag import answer
from .evaluation import evaluate

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Private ChatGPT")
db = Database(settings.database_path)
stores: dict[tuple[str, str], VectorStore] = {}
frontend_path = Path(__file__).resolve().parents[2] / "frontend" / "index.html"


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(frontend_path)


class Query(BaseModel):
    user_id: str = "demo-user"
    workspace_id: str = "default"
    question: str
    chat_id: int | None = None


class Feedback(BaseModel):
    user_id: str = "demo-user"
    chat_id: int | None = None
    rating: int
    comment: str = ""
    message_id: int | None = None
    workspace_id: str = "default"


class UserCreate(BaseModel):
    user_id: str | None = None
    display_name: str | None = None


class ChatCreate(BaseModel):
    user_id: str
    workspace_id: str = "default"
    title: str = "New chat"


class ChatUpdate(BaseModel):
    user_id: str
    workspace_id: str = "default"
    title: str


def require_user(user_id):
    if not db.users() or not any(u["id"] == user_id for u in db.users()):
        raise HTTPException(404, "user not found")


@app.get("/health")
def health():
    return {"status": "ok", "openrouter_configured": bool(settings.openrouter_api_key)}


@app.get("/users")
def list_users():
    return {"users": db.users()}


@app.post("/users")
def create_user(user: UserCreate):
    if user.user_id is not None and not user.user_id.strip():
        raise HTTPException(400, "user_id cannot be empty")
    return db.ensure_user(user.user_id.strip() if user.user_id else None, user.display_name)


@app.post("/documents")
async def upload(user_id: str = "demo-user", workspace_id: str = "default",
                 file: UploadFile = File(...)):
    require_user(user_id)
    try:
        text = extract_text(file.filename or "upload.txt", await file.read())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    chunks = chunk_text(text, settings.max_chunk_chars, settings.chunk_overlap)
    doc_id = db.add_document(user_id, workspace_id, file.filename or "upload", text, chunks)
    await asyncio.to_thread(rebuild, user_id, workspace_id)
    return {"document_id": doc_id, "chunks": len(chunks)}


@app.get("/documents")
def list_documents(user_id: str, workspace_id: str = "default"):
    require_user(user_id)
    return {"documents": db.documents(user_id, workspace_id)}


@app.delete("/documents/{document_id}")
def delete_document(document_id: int, user_id: str, workspace_id: str = "default"):
    require_user(user_id)
    if not db.delete_document(document_id, user_id, workspace_id):
        raise HTTPException(404, "document not found")
    stores.pop((user_id, workspace_id), None)
    return {"status": "deleted"}


def rebuild(user_id, workspace_id):
    rows = db.chunks(user_id, workspace_id)
    stores[(user_id, workspace_id)] = VectorStore(settings.embedding_model)
    stores[(user_id, workspace_id)].build([(r["text"], f'{r["document_id"]}:{r["chunk_index"]}') for r in rows])


@app.post("/chat")
def chat(query: Query):
    require_user(query.user_id)
    if query.chat_id is not None and not db.chat_owned(query.chat_id, query.user_id, query.workspace_id):
        raise HTTPException(404, "chat not found")
    if (query.user_id, query.workspace_id) not in stores:
        rebuild(query.user_id, query.workspace_id)
    results = stores[(query.user_id, query.workspace_id)].search(query.question)
    text, citations = answer(query.question, results)
    chat_id = query.chat_id or db.create_chat(query.user_id, query.workspace_id)
    db.add_message(chat_id, "user", query.question)
    db.add_message(chat_id, "assistant", text, json.dumps(citations))
    return {"chat_id": chat_id, "answer": text, "citations": citations}


@app.post("/chats")
def create_chat(payload: ChatCreate):
    require_user(payload.user_id)
    return {"chat_id": db.create_chat(payload.user_id, payload.workspace_id, payload.title)}


@app.get("/chats")
def list_chats(user_id: str, workspace_id: str = "default"):
    require_user(user_id)
    return {"chats": db.chats(user_id, workspace_id)}


@app.delete("/chats/{chat_id}")
def delete_chat(chat_id: int, user_id: str, workspace_id: str = "default"):
    require_user(user_id)
    if not db.delete_chat(chat_id, user_id, workspace_id):
        raise HTTPException(404, "chat not found")
    return {"status": "deleted"}


@app.patch("/chats/{chat_id}")
def update_chat(chat_id: int, payload: ChatUpdate):
    require_user(payload.user_id)
    if not db.chat_owned(chat_id, payload.user_id, payload.workspace_id):
        raise HTTPException(404, "chat not found")
    with db.connect() as conn:
        conn.execute("UPDATE chats SET title=? WHERE id=?", (payload.title.strip() or "Untitled", chat_id))
    return {"status": "updated"}


@app.get("/chats/{chat_id}/messages")
def get_chat(chat_id: int, user_id: str, workspace_id: str = "default"):
    require_user(user_id)
    if not db.chat_owned(chat_id, user_id, workspace_id):
        raise HTTPException(404, "chat not found")
    return {"messages": db.messages(chat_id, user_id, workspace_id)}


@app.post("/feedback")
def add_feedback(feedback: Feedback):
    require_user(feedback.user_id)
    if feedback.rating < 1 or feedback.rating > 5:
        raise HTTPException(400, "rating must be between 1 and 5")
    if feedback.chat_id is not None and not db.chat_owned(feedback.chat_id, feedback.user_id, feedback.workspace_id):
        raise HTTPException(404, "chat not found")
    db.add_feedback(feedback.user_id, feedback.chat_id, feedback.message_id, feedback.rating, feedback.comment)
    return {"status": "recorded"}


@app.get("/feedback")
def list_feedback(user_id: str, message_id: int | None = None):
    require_user(user_id)
    with db.connect() as conn:
        query = "SELECT * FROM feedback WHERE user_id=?"
        args = [user_id]
        if message_id is not None:
            query += " AND message_id=?"
            args.append(message_id)
        return {"feedback": [dict(row) for row in conn.execute(query, args)]}


@app.get("/stats")
def stats(user_id: str | None = None, workspace_id: str | None = None):
    if user_id:
        require_user(user_id)
    return db.stats(user_id, workspace_id)


@app.post("/evaluate")
def evaluation(payload: dict):
    return evaluate(str(payload.get("answer", "")), list(payload.get("expected_terms", [])))
