"""Advisory structured AI scoring with persistent caching and retries."""

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256

from pydantic import ValidationError

from pastila_scout.ai.cache import FileJSONCache
from pastila_scout.ai.provider import (
    ProviderError,
    StructuredAIProvider,
    StructuredAIRequest,
)
from pastila_scout.config import AIConfig, ScoringConfig
from pastila_scout.models import (
    EditorialAIResult,
    EditorialCacheDiagnostics,
    EditorialDecision,
    EditorialScoringRequest,
    TokenUsage,
)


def editorial_cache_key(
    request: EditorialScoringRequest,
    ai_config: AIConfig,
    scoring_config: ScoringConfig,
) -> str:
    """Fingerprint canonical content and every response-affecting setting."""

    payload = {
        "event": request.event.model_dump(mode="json"),
        "deterministic_score": _legacy_deterministic_payload(request),
        "scoring_schema_version": scoring_config.editorial_schema_version,
        "model": ai_config.model,
        "provider": ai_config.provider,
        "prompt_version": scoring_config.editorial_prompt_version,
        "temperature": ai_config.temperature,
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _legacy_deterministic_payload(
    request: EditorialScoringRequest,
) -> dict[str, object]:
    """Keep the Milestone 5 cache fingerprint byte-for-byte compatible."""

    score = request.deterministic_score
    return {
        "total": score.total,
        "schema_version": score.schema_version,
        "components": [
            {
                "name": item.name,
                "raw_value": item.raw_value,
                "score": item.score,
                "maximum": item.maximum,
                "reason": item.reason,
            }
            for item in score.components
        ],
    }


class EditorialEventScorer:
    """Score canonical events while isolating cache and provider failures."""

    def __init__(
        self,
        ai_config: AIConfig,
        scoring_config: ScoringConfig,
        cache: FileJSONCache,
        provider: StructuredAIProvider | None,
        *,
        api_key_available: bool,
        force_refresh: bool = False,
        sleep: Callable[[float], None] = time.sleep,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.ai_config = ai_config
        self.scoring_config = scoring_config
        self.cache = cache
        self.provider = provider
        self.api_key_available = api_key_available
        self.force_refresh = force_refresh
        self.sleep = sleep
        self.now = now
        self.ai_requests = 0

    def score(self, request: EditorialScoringRequest) -> EditorialAIResult:
        """Return a validated score or a typed non-AI/error result."""

        if not self.ai_config.enable_ai:
            return self._fallback("disabled", "AI editorial scoring is disabled")
        key = editorial_cache_key(request, self.ai_config, self.scoring_config)
        cache_status = "miss"
        if not self.force_refresh:
            cached, cache_status = self.cache.get(key)
            if cached is not None:
                try:
                    result = EditorialAIResult.model_validate(cached)
                except ValidationError:
                    cache_status = "corrupt"
                else:
                    timestamp = self.now()
                    age = max((timestamp - result.requested_at).total_seconds(), 0.0)
                    return result.model_copy(
                        update={
                            "status": "cache_hit",
                            "cache_status": "hit",
                            "cache_diagnostics": self._cache_diagnostics(
                                "hit",
                                created_at=result.requested_at,
                                cache_age_seconds=age,
                            ),
                        }
                    )
        if not self.api_key_available or self.provider is None:
            return self._fallback(
                "missing_api_key", "OpenAI API key is unavailable", cache_status
            )

        retries = 0
        latency_ms = 0.0
        while True:
            self.ai_requests += 1
            started = time.perf_counter()
            try:
                response = self.provider.complete_structured(
                    _provider_request(request, self.scoring_config)
                )
                latency_ms += (time.perf_counter() - started) * 1000
                decision = EditorialDecision.model_validate_json(response.output_text)
            except ValidationError:
                return self._fallback(
                    "invalid_response",
                    "Provider returned an invalid editorial response",
                    cache_status,
                    retries,
                    latency_ms=latency_ms,
                )
            except ProviderError as exc:
                latency_ms += (time.perf_counter() - started) * 1000
                if not exc.retryable:
                    return self._fallback(
                        "provider_error",
                        str(exc),
                        cache_status,
                        retries,
                        latency_ms=latency_ms,
                    )
                if retries >= self.ai_config.max_retries:
                    return self._fallback(
                        "retry_exhausted",
                        str(exc),
                        cache_status,
                        retries,
                        latency_ms=latency_ms,
                    )
                retries += 1
                self.sleep(self.ai_config.retry_delay)
                continue
            score = round(
                sum(
                    (
                        decision.importance,
                        decision.virality,
                        decision.absurdity,
                        decision.satirical_potential,
                        decision.public_interest,
                        decision.emotional_impact,
                        decision.originality,
                    )
                )
                / 7
                * 10,
                2,
            )
            timestamp = self.now()
            usage = _usage(response, self.scoring_config, latency_ms)
            result = EditorialAIResult(
                decision=decision,
                ai_editorial_score=score,
                provider=self.ai_config.provider,
                model=self.ai_config.model,
                prompt_version=self.scoring_config.editorial_prompt_version,
                schema_version=self.scoring_config.editorial_schema_version,
                status="success",
                requested_at=timestamp,
                retry_count=retries,
                cache_status=cache_status,
                token_usage=usage,
                cache_diagnostics=self._cache_diagnostics(
                    cache_status, created_at=timestamp
                ),
            )
            self.cache.put(key, result.model_dump(mode="json"))
            return result

    def _fallback(
        self,
        status: str,
        message: str,
        cache_status: str = "not_checked",
        retries: int = 0,
        *,
        latency_ms: float | None = None,
    ) -> EditorialAIResult:
        return EditorialAIResult(
            decision=None,
            ai_editorial_score=None,
            provider=self.ai_config.provider,
            model=self.ai_config.model,
            prompt_version=self.scoring_config.editorial_prompt_version,
            schema_version=self.scoring_config.editorial_schema_version,
            status=status,
            requested_at=self.now(),
            retry_count=retries,
            cache_status=cache_status,
            token_usage=TokenUsage(provider_latency_ms=latency_ms),
            cache_diagnostics=self._cache_diagnostics(cache_status),
            error_message=message,
        )

    def _cache_diagnostics(
        self,
        status: str,
        *,
        created_at: datetime | None = None,
        cache_age_seconds: float | None = None,
    ) -> EditorialCacheDiagnostics:
        return EditorialCacheDiagnostics(
            status=status,
            prompt_version=self.scoring_config.editorial_prompt_version,
            schema_version=self.scoring_config.editorial_schema_version,
            provider=self.ai_config.provider,
            model=self.ai_config.model,
            created_at=created_at,
            cache_age_seconds=cache_age_seconds,
        )


def _provider_request(
    request: EditorialScoringRequest, config: ScoringConfig
) -> StructuredAIRequest:
    event = request.event
    confirmed = {
        "canonical_title": event.canonical_title,
        "canonical_summary": event.canonical_summary,
        "categories": event.categories,
        "first_publication_at": event.first_publication_at,
        "last_publication_at": event.last_publication_at,
        "article_count": event.article_count,
        "source_count": event.source_count,
        "sources": [source.model_dump(mode="json") for source in event.sources],
        "articles": [
            {
                "title": article.title,
                "summary": article.summary,
                "published_at": article.published_at,
                "source_name": article.source_name,
                "url": article.url,
            }
            for article in event.articles
        ],
        "deterministic_score": request.deterministic_score.model_dump(mode="json"),
    }
    return StructuredAIRequest(
        name="editorial_event_score",
        instructions=(
            "Evaluate this Romanian news event for editorial recommendation. Use "
            "only supplied confirmed facts. Score every dimension 0-10. Keep the "
            "reason concise and list concrete editorial risks without inventing facts."
        ),
        input_json=json.dumps(confirmed, ensure_ascii=False),
        json_schema=EditorialDecision.model_json_schema(),
    )


def _usage(response: object, config: ScoringConfig, latency_ms: float) -> TokenUsage:
    input_tokens = getattr(response, "input_tokens", None)
    output_tokens = getattr(response, "output_tokens", None)
    total_tokens = getattr(response, "total_tokens", None)
    estimated = None
    if (
        input_tokens is not None
        and output_tokens is not None
        and config.input_cost_per_million_tokens is not None
        and config.output_cost_per_million_tokens is not None
    ):
        estimated = round(
            (input_tokens / 1_000_000) * config.input_cost_per_million_tokens
            + (output_tokens / 1_000_000) * config.output_cost_per_million_tokens,
            8,
        )
    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        estimated_cost=estimated,
        provider_latency_ms=round(latency_ms, 3),
    )
