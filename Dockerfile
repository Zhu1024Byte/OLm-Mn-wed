# syntax=docker/dockerfile:1.7
# ============================================================================
# OLm-Mn-wed webapp image — multi-stage, multi-arch
# Compatible with BOTH plain `docker build` (uses the local platform) and
# `docker buildx --platform linux/amd64,linux/arm64` (BuildKit resolves each
# stage to the target platform automatically).
#
# Build locally:
#   docker build -f backend/Dockerfile -t olm-mn-wed:latest .
# Run with compose:
#   docker compose up --build -d
# Multi-arch:
#   docker buildx build --platform linux/amd64,linux/arm64 \
#     -t olm-mn-wed:latest --push .
# ============================================================================

# ---- Stage 1: build the Vue frontend --------------------------------------
FROM node:20-alpine AS frontend

WORKDIR /build

# Copy the whole frontend (npm install picks up package-lock.json if present)
COPY frontend/ ./
RUN npm install --no-audit --no-fund
RUN npm run build

# ---- Stage 2: Python runtime with backend + built frontend -----------------
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# curl is used by the entrypoint to probe the Ollama service
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY backend/entrypoint.sh ./entrypoint.sh
# 兼容 Windows 检出导致的 CRLF 行尾（否则容器内 exec 失败）
RUN sed -i 's/\r$//' ./entrypoint.sh && chmod +x ./entrypoint.sh

# Built frontend -> served by FastAPI as static files
COPY --from=frontend /build/dist ./static

# Runtime directories (models is bind-mounted by compose)
RUN mkdir -p /app/data /app/models

EXPOSE 3000 3001

ENTRYPOINT ["./entrypoint.sh"]
