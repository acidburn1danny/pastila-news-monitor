"""Stable errors internal to the Ollama execution provider."""


class OllamaExecutionError(RuntimeError):
    """Base error raised by the Ollama provider implementation."""


class OllamaConnectionError(OllamaExecutionError):
    """The configured Ollama endpoint could not be reached."""


class OllamaTimeoutError(OllamaExecutionError):
    """The single HTTP request exceeded its timeout."""


class OllamaHttpError(OllamaExecutionError):
    """Ollama returned a non-successful HTTP response."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"Ollama returned HTTP {status_code}.")
        self.status_code = status_code


class OllamaModelUnavailableError(OllamaExecutionError):
    """The selected model is not installed in Ollama."""


class OllamaInvalidRequestError(OllamaExecutionError):
    """The provider rejected the mapped request."""


class OllamaMalformedResponseError(OllamaExecutionError):
    """Ollama returned a response outside the supported schema."""


__all__ = (
    "OllamaConnectionError",
    "OllamaExecutionError",
    "OllamaHttpError",
    "OllamaInvalidRequestError",
    "OllamaMalformedResponseError",
    "OllamaModelUnavailableError",
    "OllamaTimeoutError",
)
