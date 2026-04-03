FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code from backend directory
COPY backend/ ./backend/
# Main entry point needs to be at root level for some runners, or we point pythonpath
ENV PYTHONPATH=/app/backend

# Set environment for model caching to /tmp (only writable dir in HF Spaces)
ENV HF_HOME=/tmp/.cache/huggingface
ENV FASTEMBED_CACHE_PATH=/tmp/.cache/fastembed
ENV SENTENCE_TRANSFORMERS_HOME=/tmp/.cache/sentence-transformers

# Expose port 7860 (required by Hugging Face Spaces)
EXPOSE 7860

# Run FastAPI with uvicorn (pointing to nested app)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
