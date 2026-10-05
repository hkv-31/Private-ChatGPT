from dataclasses import dataclass
import numpy as np
from .config import settings

_shared_models = {}


@dataclass
class SearchResult:
    text: str
    score: float
    citation: str


class VectorStore:
    """FAISS when installed, with a deterministic cosine fallback for development."""
    def __init__(self, model_name: str):
        self.model = None
        if settings.local_embeddings:
            try:
                if model_name not in _shared_models:
                    from sentence_transformers import SentenceTransformer
                    _shared_models[model_name] = SentenceTransformer(model_name)
                self.model = _shared_models[model_name]
            except Exception:
                pass
        self.items: list[tuple[str, str]] = []
        self.vectors = None
        self.index = None

    def _embed(self, texts):
        if self.model is not None:
            return np.asarray(self.model.encode(texts, normalize_embeddings=True))
        # No model at import/runtime: lexical fallback keeps tests and demos usable.
        vocab = sorted({w for t, _ in self.items for w in t.lower().split()})
        return np.asarray([[t.lower().split().count(w) for w in vocab] for t in texts], dtype=float)

    def build(self, items: list[tuple[str, str]]):
        self.items = items
        self.vectors = self._embed([x[0] for x in items]) if items else np.empty((0, 0))
        self.index = None
        try:
            import faiss
            if len(items):
                self.index = faiss.IndexFlatIP(self.vectors.shape[1])
                self.index.add(self.vectors.astype("float32"))
        except Exception:
            pass

    def search(self, query: str, k=5) -> list[SearchResult]:
        if not self.items:
            return []
        q = self._embed([query])[0]
        if self.index is not None:
            scores, indices = self.index.search(q.astype("float32")[None, :], min(k, len(self.items)))
            pairs = zip(indices[0], scores[0])
        else:
            scores = (self.vectors @ q) / ((np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(q)) + 1e-9)
            pairs = ((i, scores[i]) for i in np.argsort(scores)[::-1][:k])
        return [SearchResult(self.items[i][0], float(score), self.items[i][1]) for i, score in pairs if i >= 0]
