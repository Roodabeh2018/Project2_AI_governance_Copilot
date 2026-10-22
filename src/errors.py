"""Shared application errors."""


class ConfigurationError(Exception):
    """Raised when required application configuration is missing or invalid."""


class IngestionError(Exception):
    """Raised when a source document cannot be loaded or validated."""


class RetrievalError(Exception):
    """Raised when indexing or retrieval fails."""


class GenerationError(Exception):
    """Raised when prompt generation or LLM generation fails."""
