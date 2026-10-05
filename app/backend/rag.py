import httpx

from .config import settings
from .vector import SearchResult


def answer(question: str, context: list[SearchResult]) -> tuple[str, list[str]]:
    citations = [item.citation for item in context]
    prompt = "\n\n".join(f"[{item.citation}] {item.text}" for item in context)
    if not settings.openrouter_api_key:
        if prompt:
            return "No OpenRouter key configured. Relevant local context:\n" + prompt, citations
        return "No OpenRouter key configured; add OPENROUTER_API_KEY to enable answers.", citations

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Answer only from the supplied context and cite sources as [filename:chunk]. "
                        "Format the response in clean Markdown: use a short opening sentence, "
                        "bold important terms with **double asterisks**, and use bullet points "
                        "for multiple details. Do not use raw HTML."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Context:\n{prompt}\n\nQuestion: {question}",
                },
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"], citations
