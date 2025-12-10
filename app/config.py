"""
app/config.py

Centralized application configuration using environment variables.

- Loads values from the OS environment and an optional `.env` file.
- Provides a single Settings object for the entire app (FastAPI + CLI).
"""
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def expand_path(path_value: str | Path) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(str(path_value))))

class Settings(BaseSettings):
    """
    Global application settings.

    Values are loaded from:
    - Environment variables
    - `.env` file in the project root (if present)

    This class is the single source of truth for configuration across:
    - FastAPI application
    - CLI tools
    - Background workers (future)
    """

    # -------------------------
    # Database
    # -------------------------
    database_url: str = Field(
        ...,
        alias="DATABASE_URL",
        description="SQLAlchemy-style database URL, e.g. postgresql+psycopg://user:pass@host:5432/dbname",
    )

    # -------------------------
    # OpenAI / LLM
    # -------------------------
    ai_provider: str = "openai"

    OPENAI_API_KEY: str | None = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    
    embedding_model_name: str = Field(
        "text-embedding-3-small",
        alias="EMBEDDING_MODEL_NAME",
        description="Default embedding model name for OpenAI provider.",
    )

    # Provider selection (Phase 11-ready)
    embedding_provider_name: str = Field(
        "openai",
        alias="EMBEDDING_PROVIDER",
        description='Embedding provider: "openai" or "ollama" (future).',
    )
    chat_provider_name: str = Field(
        "openai",
        alias="CHAT_PROVIDER",
        description='Chat provider: "openai" or "ollama" (future).',
    )

    # -------------------------
    # Filesystem paths
    # -------------------------
    ingested_dir: Path = Field(
        Path("./ingested"),
        alias="INGESTED_DIR",
        description="Directory where ingested DWG files are stored.",
    )
    derived_dir: Path = Field(
        Path("./derived"),
        alias="DERIVED_DIR",
        description="Directory where derived artifacts (DXF, PDF, PNG, JSON) are stored.",
    )

    # -------------------------
    # External tools
    # -------------------------
    dwg2dxf_path: str = Field(
        "dwg2dxf",
        alias="DWG2DXF_PATH",
        description="Path or command name for LibreDWG dwg2dxf CLI.",
    )
    dwg2json_path: str = Field(
        "./dwg2json",
        alias="DWG2JSON_PATH",
        description="Path to compiled C++ dwg2json tool.",
    )

    # -------------------------
    # Logging
    # -------------------------
    log_level: str = Field(
        "INFO",
        alias="LOG_LEVEL",
        description="Root log level (e.g., DEBUG, INFO, WARNING, ERROR).",
    )

    # -------------------------
    # Frontend / CORS
    # -------------------------
    frontend_origin: Optional[AnyHttpUrl] = Field(
        None,
        alias="FRONTEND_ORIGIN",
        description="Allowed frontend origin for CORS, e.g. http://localhost:3000",
    )

    # -------------------------
    # Optional: Local models (Ollama, Phase 11)
    # -------------------------
    ollama_base_url: Optional[AnyHttpUrl] = Field(
        None,
        alias="OLLAMA_BASE_URL",
        description="Base URL for Ollama HTTP API (if using local models).",
    )
    ollama_embedding_model: Optional[str] = Field(
        None,
        alias="OLLAMA_EMBEDDING_MODEL",
        description="Embedding model name for Ollama provider.",
    )
    ollama_chat_model: Optional[str] = Field(
        None,
        alias="OLLAMA_CHAT_MODEL",
        description="Chat model name for Ollama provider.",
    )

    # -------------------------
    # Pydantic Settings Config
    # -------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars instead of erroring
    )

    # -------------------------
    # Helper methods
    # -------------------------
    def ensure_directories(self) -> None:
        """
        Ensure that the key filesystem directories exist.

        This can be called at app startup or before running an ingestion job.
        """
        self.ingested_dir.mkdir(parents=True, exist_ok=True)
        self.derived_dir.mkdir(parents=True, exist_ok=True)
        self.ingested_dir = expand_path(self.ingested_dir)
        self.derived_dir = expand_path(self.derived_dir)

@lru_cache

def get_settings() -> Settings:
    """
    Return a cached Settings instance.

    Using lru_cache ensures we only read and parse environment variables once,
    and all parts of the application share the same configuration object.
    """
    settings = Settings()
    # Optionally ensure directories exist immediately:
    settings.ensure_directories()
    return settings

