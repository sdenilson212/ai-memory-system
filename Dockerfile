# ── Stage 1: Build UI ─────────────────────────────────────────────────────────
FROM node:20-alpine AS ui-builder

WORKDIR /app/ui
COPY ui/package*.json ./
RUN npm ci --silent
COPY ui/ ./
RUN npm run build

# ── Stage 2: Final image ──────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Engine source
COPY engine/ ./engine/

# Built UI (served via FastAPI static files)
COPY --from=ui-builder /app/ui/dist ./engine/static/

# Data volume mount point
RUN mkdir -p /data/memory-bank /data/secure

# Environment defaults (can be overridden via docker-compose or -e flags)
ENV MEMORY_DIR=/data/memory-bank
ENV API_HOST=0.0.0.0
ENV API_PORT=8765

EXPOSE 8765

WORKDIR /app/engine

CMD ["python", "main.py"]
