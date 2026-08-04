"""Direct HTTP client for Ollama's official API."""

from typing import Any

import httpx

from .errors import (
    OllamaConnectionError,
    OllamaHttpError,
    OllamaInvalidRequestError,
    OllamaMalformedResponseError,
    OllamaModelUnavailableError,
    OllamaTimeoutError,
)
from .models import OllamaChatRequestV1


class OllamaHttpClientV1:
    """Use an injected HTTP client; transport lifetime remains with its owner."""

    def __init__(self, client: httpx.Client) -> None:
        if type(client) is not httpx.Client:
            raise _isolated(TypeError("client must be an httpx.Client"))
        self._client = client

    def chat(self, request: OllamaChatRequestV1, base_url: str, timeout: float) -> Any:
        """Perform exactly one non-streaming request with exactly one timeout."""
        timeout_error = False
        connection_error = False
        try:
            response = self._client.post(
                f"{base_url}/api/chat",
                json=request.model_dump(mode="json"),
                timeout=timeout,
            )
        except httpx.TimeoutException:
            timeout_error = True
        except httpx.RequestError:
            connection_error = True
        if timeout_error:
            raise _isolated(OllamaTimeoutError("Ollama request timed out"))
        if connection_error:
            raise _isolated(OllamaConnectionError("Ollama connection failed"))
        error_text = _error_text(response)
        if _is_missing_model(response.status_code, error_text):
            raise _isolated(OllamaModelUnavailableError("Ollama model is unavailable"))
        if response.status_code in {400, 422}:
            raise _isolated(OllamaInvalidRequestError("Ollama rejected the request"))
        if not response.is_success:
            raise _isolated(OllamaHttpError(response.status_code))
        malformed_json = False
        try:
            payload = response.json()
        except ValueError:
            malformed_json = True
            payload = None
        if malformed_json:
            raise _isolated(
                OllamaMalformedResponseError("Ollama returned invalid JSON")
            )
        if isinstance(payload, dict) and isinstance(payload.get("error"), str):
            if _is_missing_model(response.status_code, payload["error"]):
                raise _isolated(
                    OllamaModelUnavailableError("Ollama model is unavailable")
                )
            raise _isolated(OllamaHttpError(response.status_code))
        return payload


def _error_text(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    if isinstance(payload, dict) and isinstance(payload.get("error"), str):
        return payload["error"]
    return ""


def _is_missing_model(status_code: int, error_text: str) -> bool:
    lowered = error_text.lower()
    return status_code in {200, 404} and "model" in lowered and "not found" in lowered


def _isolated[ErrorT: BaseException](error: ErrorT) -> ErrorT:
    error.__suppress_context__ = True
    return error


__all__ = ("OllamaHttpClientV1",)
