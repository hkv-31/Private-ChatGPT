def chunk_text(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    if overlap >= max_chars:
        raise ValueError("overlap must be smaller than max_chars")
    chunks, start = [], 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            boundary = text.rfind(" ", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks
