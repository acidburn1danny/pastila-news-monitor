"""Provider-neutral structured generation boundary and offline scripted provider."""

from collections import deque
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor.generation.prompt import GenerationPrompt

T = TypeVar("T", bound=BaseModel)


class ProviderError(RuntimeError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderAuthenticationError(ProviderError):
    pass


class ProviderRateLimitError(ProviderError):
    pass


class ProviderUnavailableError(ProviderError):
    pass


class ProviderStructuredOutputError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class LanguageModelProvider(Protocol):
    provider_identifier: str

    def generate_structured(
        self,
        *,
        prompt: GenerationPrompt,
        output_schema: type[T],
        config: LanguageGenerationConfig,
    ) -> T: ...


class ScriptedLanguageModelProvider:
    """Return queued responses/errors and record every offline provider call."""

    provider_identifier = "scripted"

    def __init__(self, responses):
        self._responses = deque(responses)
        self.prompts = []
        self.schemas = []
        self.configs = []
        self.call_order = []

    def generate_structured(self, *, prompt, output_schema, config):
        self.prompts.append(prompt)
        self.schemas.append(output_schema)
        self.configs.append(config)
        self.call_order.append(prompt.component_type)
        if not self._responses:
            raise ProviderResponseError("scripted response queue exhausted")
        value = self._responses.popleft()
        if isinstance(value, BaseException):
            raise value
        try:
            return (
                value
                if isinstance(value, output_schema)
                else output_schema.model_validate(value)
            )
        except ValidationError as exc:
            raise ProviderStructuredOutputError(str(exc)) from exc
