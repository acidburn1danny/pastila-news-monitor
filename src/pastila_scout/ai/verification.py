"""Structured validation, retry handling, and advisory confirmation rules."""

import time
from collections.abc import Callable
from datetime import UTC, datetime

from pydantic import ValidationError

from pastila_scout.ai.cache import VerificationCache, verification_cache_key
from pastila_scout.ai.provider import AIProvider, ProviderError
from pastila_scout.config import AIConfig
from pastila_scout.models.ai import (
    AICacheDiagnostics,
    AIUsageDiagnostics,
    AIVerificationResult,
    EventVerificationRequest,
    ProviderVerificationDecision,
)


def confirms_same_event(result: AIVerificationResult) -> bool:
    """Apply the fixed advisory confirmation threshold."""

    return (
        result.same_event
        and result.ai_similarity_score >= 85
        and result.same_people is not False
        and result.same_institution is not False
        and result.same_location is not False
        and result.same_context is True
    )


class EventVerifier:
    """Verify candidate pairs without persistence knowledge or side effects."""

    def __init__(
        self,
        config: AIConfig,
        cache: VerificationCache,
        provider: AIProvider | None,
        *,
        api_key_available: bool,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        input_cost_per_million_tokens: float | None = None,
        output_cost_per_million_tokens: float | None = None,
    ) -> None:
        self.config = config
        self.cache = cache
        self.provider = provider
        self.api_key_available = api_key_available
        self.sleep = sleep
        self.now = now
        self.ai_requests = 0
        self.input_cost_per_million_tokens = input_cost_per_million_tokens
        self.output_cost_per_million_tokens = output_cost_per_million_tokens

    def verify(self, request: EventVerificationRequest) -> AIVerificationResult:
        key = verification_cache_key(request, self.config)
        lookup = self.cache.get(key)
        if lookup.result is not None:
            timestamp = self.now()
            age = max((timestamp - lookup.result.requested_at).total_seconds(), 0.0)
            return lookup.result.model_copy(
                update={
                    "status": "cache_hit",
                    "cache_status": "hit",
                    "cache_diagnostics": self._cache_diagnostics(
                        "hit",
                        created_at=lookup.result.requested_at,
                        cache_age_seconds=age,
                    ),
                }
            )
        if not self.config.enable_ai:
            return self._fallback(
                "disabled", "AI verification is disabled", lookup.status
            )
        if not self.api_key_available or self.provider is None:
            return self._fallback(
                "missing_api_key", "OpenAI API key is unavailable", lookup.status
            )

        retries = 0
        latency_ms = 0.0
        while True:
            self.ai_requests += 1
            started = time.perf_counter()
            try:
                diagnostic_method = getattr(
                    self.provider, "verify_with_diagnostics", None
                )
                if callable(diagnostic_method):
                    response = diagnostic_method(request)
                    raw = response.output_text
                else:
                    response = None
                    raw = self.provider.verify(request)
                latency_ms += (time.perf_counter() - started) * 1000
                decision = ProviderVerificationDecision.model_validate_json(raw)
            except ValidationError:
                return self._fallback(
                    "invalid_response",
                    "Provider returned an invalid structured response",
                    lookup.status,
                    retries,
                    latency_ms=latency_ms,
                )
            except ProviderError as exc:
                latency_ms += (time.perf_counter() - started) * 1000
                if not exc.retryable:
                    return self._fallback(
                        "provider_error",
                        str(exc),
                        lookup.status,
                        retries,
                        latency_ms=latency_ms,
                    )
                if retries >= self.config.max_retries:
                    return self._fallback(
                        "retry_exhausted",
                        str(exc),
                        lookup.status,
                        retries,
                        latency_ms=latency_ms,
                    )
                retries += 1
                self.sleep(self.config.retry_delay)
                continue
            timestamp = self.now()
            usage = self._usage(response, latency_ms)
            result = AIVerificationResult(
                **decision.model_dump(),
                provider=self.config.provider,
                model=self.config.model,
                prompt_version=self.config.prompt_version,
                status="success",
                requested_at=timestamp,
                retry_count=retries,
                cache_status=lookup.status,
                usage=usage,
                cache_diagnostics=self._cache_diagnostics(
                    lookup.status, created_at=timestamp
                ),
            )
            self.cache.put(key, result)
            return result

    def _fallback(
        self,
        status: str,
        reason: str,
        cache_status: str,
        retries: int = 0,
        *,
        latency_ms: float | None = None,
    ) -> AIVerificationResult:
        return AIVerificationResult(
            same_event=False,
            ai_similarity_score=0,
            same_people=None,
            same_institution=None,
            same_location=None,
            same_context=None,
            reasoning=reason,
            provider=self.config.provider,
            model=self.config.model,
            prompt_version=self.config.prompt_version,
            status=status,
            requested_at=self.now(),
            retry_count=retries,
            cache_status=cache_status,
            usage=AIUsageDiagnostics(provider_latency_ms=latency_ms),
            cache_diagnostics=self._cache_diagnostics(cache_status),
        )

    def _usage(self, response: object | None, latency_ms: float) -> AIUsageDiagnostics:
        input_tokens = getattr(response, "input_tokens", None)
        output_tokens = getattr(response, "output_tokens", None)
        total_tokens = getattr(response, "total_tokens", None)
        estimated = None
        if (
            input_tokens is not None
            and output_tokens is not None
            and self.input_cost_per_million_tokens is not None
            and self.output_cost_per_million_tokens is not None
        ):
            estimated = round(
                (input_tokens / 1_000_000) * self.input_cost_per_million_tokens
                + (output_tokens / 1_000_000) * self.output_cost_per_million_tokens,
                8,
            )
        return AIUsageDiagnostics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            provider_latency_ms=round(latency_ms, 3),
            estimated_cost=estimated,
        )

    def _cache_diagnostics(
        self,
        status: str,
        *,
        created_at: datetime | None = None,
        cache_age_seconds: float | None = None,
    ) -> AICacheDiagnostics:
        return AICacheDiagnostics(
            status=status,
            prompt_version=self.config.prompt_version,
            provider=self.config.provider,
            model=self.config.model,
            created_at=created_at,
            cache_age_seconds=cache_age_seconds,
        )
