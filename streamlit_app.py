import requests
import streamlit as st
from requests import RequestException

st.set_page_config(page_title="Private ChatGPT", page_icon="🔒", layout="wide")
st.title("🔒 Private ChatGPT")
api = st.sidebar.text_input("Backend URL", "http://localhost:8000")


def request_json(method, path, **kwargs):
    try:
        response = requests.request(method, f"{api}{path}", timeout=20, **kwargs)
        response.raise_for_status()
        return response.json()
    except RequestException as exc:
        st.error(
            f"Could not reach the FastAPI backend at {api}. "
            "Start it with `uvicorn app.backend.main:app --reload`, then reload this page. "
            f"Details: {exc}"
        )
        st.stop()


users = request_json("GET", "/users").get("users", [])
names = {u["id"]: u["display_name"] for u in users}
chosen = st.sidebar.selectbox("Active user", list(names) or ["demo-user"],
                              format_func=lambda x: names.get(x, x))
with st.sidebar.expander("New user"):
    new_name = st.text_input("Display name")
    if st.button("Create user") and new_name.strip():
        r = requests.post(f"{api}/users", json={"display_name": new_name.strip()}, timeout=20)
        st.rerun() if r.ok else st.error(r.text)
workspace = st.sidebar.text_input("Workspace", st.query_params.get("workspace", "default"))
st.query_params["user"] = chosen
st.query_params["workspace"] = workspace

def get(path, **kwargs):
    return request_json("GET", path, **kwargs)

tabs = st.tabs(["Chat", "Documents", "History", "Feedback & stats"])
with tabs[1]:
    upload = st.file_uploader("Upload PDF, DOCX, TXT, Markdown, or image")
    if upload and st.button("Index document"):
        r = requests.post(f"{api}/documents", params={"user_id": chosen, "workspace_id": workspace},
                          files={"file": (upload.name, upload.getvalue())}, timeout=90)
        st.success(r.json() if r.ok else r.text)
    docs = get("/documents", params={"user_id": chosen, "workspace_id": workspace}).get("documents", [])
    for doc in docs:
        col1, col2 = st.columns([4, 1])
        col1.write(f"📄 {doc['filename']}")
        if col2.button("Delete", key=f"doc-{doc['id']}"):
            requests.delete(f"{api}/documents/{doc['id']}",
                            params={"user_id": chosen, "workspace_id": workspace}, timeout=20)
            st.rerun()
with tabs[2]:
    chats = get("/chats", params={"user_id": chosen, "workspace_id": workspace}).get("chats", [])
    for item in chats:
        if st.button(f"{item['title']} (#{item['id']})", key=f"chat-{item['id']}"):
            st.session_state["chat_id"] = item["id"]
        if st.button("Delete", key=f"delete-chat-{item['id']}"):
            requests.delete(f"{api}/chats/{item['id']}",
                            params={"user_id": chosen, "workspace_id": workspace}, timeout=20)
            st.rerun()
    if chats:
        selected = st.session_state.get("chat_id", chats[0]["id"])
        history = get(f"/chats/{selected}/messages",
                      params={"user_id": chosen, "workspace_id": workspace})
        for message in history.get("messages", []):
            with st.chat_message(message["role"]):
                st.write(message["content"])
with tabs[3]:
    stats = get("/stats", params={"user_id": chosen, "workspace_id": workspace})
    st.json(stats)
    rating = st.slider("Rate the current answer", 1, 5, 5)
    comment = st.text_area("Feedback")
    if st.button("Submit feedback"):
        r = requests.post(f"{api}/feedback", json={"user_id": chosen, "rating": rating,
                                                   "comment": comment, "workspace_id": workspace})
        st.success("Recorded" if r.ok else r.text)
with tabs[0]:
    question = st.chat_input("Ask about your documents")
    if question:
        with st.chat_message("user"):
            st.write(question)
        payload = {"user_id": chosen, "workspace_id": workspace, "question": question,
                   "chat_id": st.session_state.get("chat_id")}
        r = requests.post(f"{api}/chat", json=payload, timeout=120)
        with st.chat_message("assistant"):
            if r.ok:
                data = r.json()
                st.session_state["chat_id"] = data["chat_id"]
                st.write(data["answer"])
                st.caption("Citations: " + ", ".join(data["citations"]) if data["citations"] else "No citations")
            else:
                st.error(r.text)
