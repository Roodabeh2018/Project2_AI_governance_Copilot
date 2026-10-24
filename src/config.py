"""Configuration contract (§8): environment variables are read ONLY here."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from src.contracts import ConfigurationError

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv not installed
    def load_dotenv(*_a, **_k):
        return False

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PRIMARY_DIR = ROOT / "knowledge_base" / "primary"
SECONDARY_DIR = ROOT / "knowledge_base" / "secondary"
CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "outputs"
FIXTURES_DIR = ROOT / "tests" / "fixtures"
DATA_DIR = ROOT / "data"


@dataclass
class AppConfig:
    model_name: str
    embedding_model: str
    top_k_primary: int
    top_k_secondary: int
    minimum_retrieval_score: float


def load_config() -> AppConfig:
    return AppConfig(
        model_name=os.getenv("MODEL_NAME") or "gpt-4o-mini",
        embedding_model=os.getenv("EMBEDDING_MODEL") or "text-embedding-3-small",
        top_k_primary=int(os.getenv("TOP_K_PRIMARY", "3")),
        top_k_secondary=int(os.getenv("TOP_K_SECONDARY", "3")),
        minimum_retrieval_score=float(os.getenv("MIN_RETRIEVAL_SCORE", "0.35")),
    )


def get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise ConfigurationError("OPENAI_API_KEY is missing. Copy .env.example to .env and add your key.")
    return key


def llm_provider() -> str:
    """'openai' (default) or 'mock' for free offline tests (LLM_PROVIDER=mock)."""
    return os.getenv("LLM_PROVIDER", "openai").lower()


def launch_settings(environ=None) -> dict:
    """Gradio launch arguments (contract §8: environment variables are read only here).

    - Locally (no PORT): 127.0.0.1:7860.
    - On a server (PORT set, e.g. Render): 0.0.0.0 and that port.
    - Login: APP_USERNAME and APP_PASSWORD must be set together. Only one of them set (or one empty)
      is a ConfigurationError, so a typo never silently exposes the app without its login.
      Neither set means no login (intended for local use).
    """
    env = os.environ if environ is None else environ
    port = env.get("PORT", "").strip()
    user = env.get("APP_USERNAME", "").strip()
    password = env.get("APP_PASSWORD", "").strip()
    if bool(user) != bool(password):
        missing = "APP_PASSWORD" if user else "APP_USERNAME"
        raise ConfigurationError(f"Login is half configured: {missing} is missing or empty. "
                                 "Set both APP_USERNAME and APP_PASSWORD, or neither.")
    try:
        server_port = int(port) if port else 7860
    except ValueError as exc:
        raise ConfigurationError(f"PORT must be a number, got {port!r}.") from exc
    return {"server_name": "0.0.0.0" if port else "127.0.0.1",
            "server_port": server_port,
            "auth": (user, password) if user else None}
