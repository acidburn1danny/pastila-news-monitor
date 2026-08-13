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

    def check_model(self, *, model: str, base_url: str, timeout: float) -> None:
        """Verify the local server and configured model without generation."""
        try:
            version = self._client.get(f"{base_url}/api/version", timeout=timeout)
            tags = self._client.get(f"{base_url}/api/tags", timeout=timeout)
        except httpx.TimeoutException:
            raise _isolated(OllamaTimeoutError("Ollama availability check timed out"))
        except httpx.RequestError:
            raise _isolated(OllamaConnectionError("Ollama connection failed"))
        if not version.is_success or not tags.is_success:
            raise _isolated(OllamaHttpError(tags.status_code))
        try:
            version_payload = version.json()
            payload = tags.json()
            models = payload["models"]
            names = {
                item["name"]
                for item in models
                if type(item) is dict and type(item.get("name")) is str
            }
            if (
                type(version_payload) is not dict
                or type(version_payload.get("version")) is not str
                or type(models) is not list
            ):
                raise TypeError
        except (TypeError, KeyError, ValueError):
            raise _isolated(OllamaMalformedResponseError("Ollama returned invalid discovery data"))
        if model not in names:
            raise _isolated(OllamaModelUnavailableError("Ollama model is unavailable"))

    def list_models(self, *, base_url: str, timeout: float) -> tuple[str, ...]:
        """Return exact installed model names from Ollama discovery."""
        try:
            response = self._client.get(f"{base_url}/api/tags", timeout=timeout)
        except httpx.TimeoutException:
            raise _isolated(OllamaTimeoutError("Ollama availability check timed out"))
        except httpx.RequestError:
            raise _isolated(OllamaConnectionError("Ollama connection failed"))
        if not response.is_success:
            raise _isolated(OllamaHttpError(response.status_code))
        try:
            models = response.json()["models"]
            names = tuple(
                item["name"]
                for item in models
                if type(item) is dict and type(item.get("name")) is str
            )
            if type(models) is not list:
                raise TypeError
            return names
        except (TypeError, KeyError, ValueError):
            raise _isolated(
                OllamaMalformedResponseError("Ollama returned invalid discovery data")
            )


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
