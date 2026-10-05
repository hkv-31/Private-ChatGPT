from app.backend.chunking import chunk_text
from app.backend.evaluation import evaluate
from app.backend.extract import extract_text
from app.backend.db import Database


def test_chunking_overlap_and_empty():
    assert chunk_text("") == []
    chunks = chunk_text("one " * 500, 100, 10)
    assert len(chunks) > 1


def test_text_extraction():
    assert "hello" in extract_text("x.txt", b"hello")


def test_evaluation():
    assert evaluate("The answer has Python", ["python"])["term_recall"] == 1


def test_database_isolates_users_and_supports_crud(tmp_path):
    db = Database(tmp_path / "x.db")
    db.ensure_user("alice", "Alice")
    db.ensure_user("bob", "Bob")
    chat = db.create_chat("alice", "w")
    assert db.chat_owned(chat, "alice", "w")
    assert not db.chat_owned(chat, "bob", "w")
    assert db.delete_chat(chat, "bob", "w") is False
    assert db.delete_chat(chat, "alice", "w") is True
