FROM python:3.11-slim
WORKDIR /app
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt
COPY . .
# Small hosted instances should use the dependency-free lexical retriever unless
# semantic embeddings are explicitly enabled through the deployment environment.
ENV LOCAL_EMBEDDINGS=false
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
