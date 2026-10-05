import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, display_name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS documents (
 id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
 filename TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS chunks (
 id INTEGER PRIMARY KEY, document_id INTEGER NOT NULL, user_id TEXT NOT NULL,
 workspace_id TEXT NOT NULL, chunk_index INTEGER NOT NULL, text TEXT NOT NULL,
 FOREIGN KEY(document_id) REFERENCES documents(id));
CREATE TABLE IF NOT EXISTS chats (
 id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, workspace_id TEXT NOT NULL,
 title TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages (
 id INTEGER PRIMARY KEY, chat_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,
 citations TEXT DEFAULT '[]', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(chat_id) REFERENCES chats(id));
CREATE TABLE IF NOT EXISTS feedback (
 id INTEGER PRIMARY KEY, user_id TEXT NOT NULL, chat_id INTEGER, message_id INTEGER, rating INTEGER,
 comment TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(feedback)")}
            if "message_id" not in columns:
                conn.execute("ALTER TABLE feedback ADD COLUMN message_id INTEGER")
            conn.execute("INSERT OR IGNORE INTO users(id,display_name) VALUES('demo-user','Demo User')")

    def ensure_user(self, user_id=None, display_name=None):
        if not user_id:
            with self.connect() as c:
                rows = c.execute("SELECT id FROM users WHERE id LIKE 'user_%'").fetchall()
            used = {row["id"] for row in rows}
            number = 1
            while f"user_{number:03d}" in used:
                number += 1
            user_id = f"user_{number:03d}"
        with self.connect() as c:
            c.execute("INSERT OR IGNORE INTO users(id,display_name) VALUES(?,?)",
                      (user_id, display_name or user_id))
        return {"id": user_id, "display_name": display_name or user_id}

    def users(self):
        with self.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM users ORDER BY id")]

    def documents(self, user_id, workspace_id):
        with self.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT id,filename,workspace_id,created_at FROM documents WHERE user_id=? AND workspace_id=? ORDER BY id DESC",
                (user_id, workspace_id))]

    def delete_document(self, doc_id, user_id, workspace_id):
        with self.connect() as c:
            row = c.execute("SELECT id FROM documents WHERE id=? AND user_id=? AND workspace_id=?",
                            (doc_id, user_id, workspace_id)).fetchone()
            if not row:
                return False
            c.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
            c.execute("DELETE FROM documents WHERE id=?", (doc_id,))
            return True

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def add_document(self, user_id, workspace_id, filename, content, chunks):
        with self.connect() as c:
            cur = c.execute("INSERT INTO documents(user_id,workspace_id,filename,content) VALUES(?,?,?,?)",
                            (user_id, workspace_id, filename, content))
            doc_id = cur.lastrowid
            c.executemany("INSERT INTO chunks(document_id,user_id,workspace_id,chunk_index,text) VALUES(?,?,?,?,?)",
                          [(doc_id, user_id, workspace_id, i, text) for i, text in enumerate(chunks)])
        return doc_id

    def chunks(self, user_id, workspace_id):
        with self.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM chunks WHERE user_id=? AND workspace_id=? ORDER BY document_id,chunk_index",
                (user_id, workspace_id))]

    def create_chat(self, user_id, workspace_id, title="New chat"):
        with self.connect() as c:
            return c.execute("INSERT INTO chats(user_id,workspace_id,title) VALUES(?,?,?)",
                             (user_id, workspace_id, title)).lastrowid

    def chats(self, user_id, workspace_id):
        with self.connect() as c:
            return [dict(r) for r in c.execute(
                "SELECT * FROM chats WHERE user_id=? AND workspace_id=? ORDER BY id DESC",
                (user_id, workspace_id))]

    def chat_owned(self, chat_id, user_id, workspace_id):
        with self.connect() as c:
            return c.execute("SELECT id FROM chats WHERE id=? AND user_id=? AND workspace_id=?",
                             (chat_id, user_id, workspace_id)).fetchone() is not None

    def delete_chat(self, chat_id, user_id, workspace_id):
        if not self.chat_owned(chat_id, user_id, workspace_id):
            return False
        with self.connect() as c:
            c.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
            c.execute("DELETE FROM feedback WHERE chat_id=?", (chat_id,))
            c.execute("DELETE FROM chats WHERE id=?", (chat_id,))
        return True

    def add_message(self, chat_id, role, content, citations="[]"):
        with self.connect() as c:
            c.execute("INSERT INTO messages(chat_id,role,content,citations) VALUES(?,?,?,?)",
                      (chat_id, role, content, citations))

    def messages(self, chat_id, user_id=None, workspace_id=None):
        with self.connect() as c:
            if user_id is not None:
                owned = c.execute("SELECT id FROM chats WHERE id=? AND user_id=? AND workspace_id=?",
                                  (chat_id, user_id, workspace_id)).fetchone()
                if not owned:
                    return []
            return [dict(r) for r in c.execute("SELECT * FROM messages WHERE chat_id=? ORDER BY id", (chat_id,))]

    def add_feedback(self, user_id, chat_id, message_id, rating, comment):
        with self.connect() as c:
            c.execute("INSERT INTO feedback(user_id,chat_id,message_id,rating,comment) VALUES(?,?,?,?,?)",
                      (user_id, chat_id, message_id, rating, comment))

    def stats(self, user_id=None, workspace_id=None):
        with self.connect() as c:
            document_scope = " WHERE user_id=?" if user_id else ""
            workspace_scope = " AND workspace_id=?" if user_id and workspace_id else ""
            args = ((user_id,) if user_id else ()) + ((workspace_id,) if user_id and workspace_id else ())
            chat_scope = " WHERE user_id=?" + workspace_scope if user_id else ""
            feedback_scope = " WHERE user_id=?" if user_id else ""
            feedback_args = (user_id,) if user_id else ()
            feedback_count = c.execute("SELECT COUNT(*) FROM feedback" + feedback_scope, feedback_args).fetchone()[0]
            positive = c.execute("SELECT COUNT(*) FROM feedback" + feedback_scope +
                                 (" AND rating >= 4" if feedback_scope else " WHERE rating >= 4"),
                                 feedback_args).fetchone()[0]
            negative = c.execute("SELECT COUNT(*) FROM feedback" + feedback_scope +
                                 (" AND rating <= 2" if feedback_scope else " WHERE rating <= 2"),
                                 feedback_args).fetchone()[0]
            return {
                "documents": c.execute("SELECT COUNT(*) FROM documents" + document_scope + workspace_scope, args).fetchone()[0],
                "chats": c.execute("SELECT COUNT(*) FROM chats" + chat_scope, args).fetchone()[0],
                "messages": c.execute("SELECT COUNT(*) FROM messages WHERE chat_id IN (SELECT id FROM chats" +
                                      chat_scope + ")", args).fetchone()[0],
                "feedback": feedback_count,
                "positive_feedback": positive,
                "negative_feedback": negative,
                "positive_percentage": round(positive * 100 / feedback_count, 1) if feedback_count else 0,
                "negative_percentage": round(negative * 100 / feedback_count, 1) if feedback_count else 0,
                "average_rating": c.execute("SELECT AVG(rating) FROM feedback" + feedback_scope, feedback_args).fetchone()[0],
            }
