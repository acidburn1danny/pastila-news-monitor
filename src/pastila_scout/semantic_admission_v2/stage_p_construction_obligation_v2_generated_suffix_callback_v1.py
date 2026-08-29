"""Prompt-once, request-bound generated-suffix callback candidate."""
from __future__ import annotations
import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptOnceBindingV1:
    request_identity: str
    prompt_token_sha256: str
    prompt_token_count: int


class RequestBoundGeneratedSuffixCallbackV1:
    def __init__(self, *, request_identity: str, prompt_token_ids: Sequence[int],
                 project: Callable[[Sequence[int]], object]) -> None:
        if not request_identity or not callable(project):
            raise ValueError("GENERATED_SUFFIX_CALLBACK_BINDING_INVALID")
        prompt = _exact_ids(prompt_token_ids, "PROMPT")
        self.binding = PromptOnceBindingV1(
            request_identity, _ids_identity(prompt), len(prompt))
        self._prompt = prompt
        self._project = project
        self._last_generated: tuple[int, ...] = ()
        self._active = True

    def validate_prompt_once(self, *, request_identity: str,
                             prompt_token_ids: Sequence[int]) -> None:
        if request_identity != self.binding.request_identity:
            raise ValueError("GENERATED_SUFFIX_CROSS_REQUEST")
        if _exact_ids(prompt_token_ids, "PROMPT") != self._prompt:
            raise ValueError("GENERATED_SUFFIX_PROMPT_SUBSTITUTION")

    def project_generated_suffix(self, *, request_identity: str,
                                 generated_token_ids: Sequence[int]) -> object:
        if not self._active:
            raise ValueError("GENERATED_SUFFIX_STALE_CALLBACK")
        if request_identity != self.binding.request_identity:
            raise ValueError("GENERATED_SUFFIX_CROSS_REQUEST")
        generated = _exact_ids(generated_token_ids, "GENERATED")
        if (len(generated) < len(self._last_generated)
                or generated[:len(self._last_generated)] != self._last_generated):
            raise ValueError("GENERATED_SUFFIX_NONINCREMENTAL_OR_MUTATED")
        result = self._project(generated)
        self._last_generated = generated
        return result

    def close(self) -> None:
        self._active = False


def _exact_ids(values: Sequence[int], label: str) -> tuple[int, ...]:
    result = tuple(values)
    if any(type(value) is not int or value < 0 for value in result):
        raise ValueError(f"GENERATED_SUFFIX_{label}_TOKENS_INVALID")
    return result


def _ids_identity(values: Sequence[int]) -> str:
    raw = ",".join(map(str, values)).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


__all__ = ("PromptOnceBindingV1", "RequestBoundGeneratedSuffixCallbackV1")
