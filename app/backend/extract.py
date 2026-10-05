from pathlib import Path


def extract_text(path: str | Path, data: bytes | None = None) -> str:
    """Extract common document formats; optional libraries fail gracefully."""
    path = Path(path)
    raw = data if data is not None else path.read_bytes()
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".markdown"}:
        return raw.decode("utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
            import io
            return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
        except Exception:
            return "[PDF text extraction unavailable; install pypdf]"
    if ext == ".docx":
        try:
            from docx import Document
            import io
            return "\n".join(p.text for p in Document(io.BytesIO(raw)).paragraphs)
        except Exception:
            return "[DOCX text extraction unavailable; install python-docx]"
    if ext in {".png", ".jpg", ".jpeg", ".tiff", ".bmp"}:
        try:
            import pytesseract
            from PIL import Image
            import io
            return pytesseract.image_to_string(Image.open(io.BytesIO(raw)))
        except Exception:
            return "[OCR unavailable; install pillow, pytesseract, and the Tesseract binary]"
    raise ValueError(f"Unsupported file type: {ext}")
