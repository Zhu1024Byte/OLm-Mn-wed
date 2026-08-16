"""Application settings, overridable through environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration.

    Every field can be overridden with an environment variable of the same
    name (case-insensitive), e.g. ``OLLAMA_BASE_URL`` -> ``ollama_base_url``.
    """

    # Application identity
    app_name: str = "OLm-Mn-wed"
    version: str = "0.1.0"

    # ---- Services (container-internal ports) ----
    # Web UI service port
    web_port: int = 3000
    # OpenAI-compatible API service port (optional service)
    api_port: int = 3001
    # Whether the API service is started on boot
    api_enabled: bool = True

    # ---- Ollama ----
    # Inside the compose network the service is reachable as http://ollama:11434
    ollama_base_url: str = "http://ollama:11434"
    # Upstream API style: "ollama" (native) or "openai" (OpenAI-compatible,
    # e.g. llama-swap / llama.cpp server / vLLM)
    ollama_api_style: str = "ollama"
    # Embedding model used by the knowledge base (RAG)
    embed_model: str = "nomic-embed-text"
    # GitHub repo for project update checks, e.g. "someone/olm-mn-wed"
    # (empty = skip the project update check)
    project_repo: str = ""

    # ---- Storage ----
    # SQLite database file (absolute path inside the container)
    database_path: str = "data/olmwed.db"
    # Directory holding GGUF files (webapp container view: /app/models)
    models_dir: str = "models"

    # ---- Auth ----
    # JWT signing secret; empty means "auto-generate and persist to
    # data/.secret_key" so tokens survive restarts.
    secret_key: str = ""
    # JWT lifetime in minutes
    jwt_expire_minutes: int = 60 * 24 * 7

    # ---- CORS ----
    # Comma-separated origins; "*" allows all (dev convenience only,
    # production serves the UI from the same origin).
    cors_origins: str = "*"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
