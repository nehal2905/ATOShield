# Build context is the repo root (see docker-compose.yml) so we can copy ml/.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps (build tools for some wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Install backend deps first (better layer caching)
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install -r /app/backend/requirements.txt

# Copy the ML package (features.py is shared) and backend app
COPY ml /app/ml
COPY backend /app/backend

# The ml package must be importable as `ml`
ENV PYTHONPATH=/app

WORKDIR /app/backend

EXPOSE 8000

# Run migrations then start the server (entrypoint handles ordering)
CMD ["bash", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
