#!/bin/sh
# ============================================================================
# OLm-Mn-wed container entrypoint
# Starts the Web service (port 3000) and, when enabled, the
# OpenAI-compatible API service (port 3001) as background processes.
#
# The API port can be overridden at runtime from the web UI
# (data/settings.json) and takes effect after a restart: if the API_PORT
# environment variable is not set, it is read from settings.json.
# ============================================================================
set -e

WEB_PORT="${WEB_PORT:-3000}"
API_PORT="${API_PORT:-}"

# Read the API port from runtime settings when the env var is not provided
if [ -z "${API_PORT}" ] && [ -f /app/data/settings.json ]; then
  API_PORT=$(python -c "import json;print(json.load(open('/app/data/settings.json')).get('api_port', 3001))" 2>/dev/null || true)
fi
API_PORT="${API_PORT:-3001}"

echo "[entrypoint] Starting web service on port ${WEB_PORT} ..."
uvicorn app.main:app --host 0.0.0.0 --port "${WEB_PORT}" &

if [ "${API_ENABLED:-true}" = "true" ]; then
  echo "[entrypoint] Starting OpenAI-compatible API service on port ${API_PORT} ..."
  uvicorn app.api_app:app --host 0.0.0.0 --port "${API_PORT}" &
else
  echo "[entrypoint] API service disabled (API_ENABLED != true)."
fi

# Keep the container alive as long as any service runs
wait
