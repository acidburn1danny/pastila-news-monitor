"""Versioned benchmark-only provider pricing assumptions."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class BenchmarkPricingSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["controlled-revision-provider-pricing-v1"]
    provider: Literal["openai"]
    model: Literal["gpt-4.1-mini"]
    currency: Literal["USD"]
    pricing_version: str = Field(pattern=r"^[a-z0-9-]+$")
    effective_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    input_per_1m_tokens: float = Field(ge=0)
    cached_input_per_1m_tokens: float = Field(ge=0)
    output_per_1m_tokens: float = Field(ge=0)
    reasoning_per_1m_tokens: float | None = Field(default=None, ge=0)
    pricing_source: str = Field(min_length=1, max_length=200)
    estimated_cost: Literal[True]

    def estimate_cost(
        self,
        *,
        input_tokens: int,
        cached_input_tokens: int,
        output_tokens: int,
        reasoning_tokens: int = 0,
    ) -> float:
        if min(input_tokens, cached_input_tokens, output_tokens, reasoning_tokens) < 0:
            raise ValueError("benchmark token counts must be non-negative")
        if cached_input_tokens > input_tokens:
            raise ValueError("cached input exceeds total input")
        uncached = input_tokens - cached_input_tokens
        reasoning_rate = self.reasoning_per_1m_tokens or self.output_per_1m_tokens
        return (
            uncached * self.input_per_1m_tokens
            + cached_input_tokens * self.cached_input_per_1m_tokens
            + output_tokens * self.output_per_1m_tokens
            + reasoning_tokens * reasoning_rate
        ) / 1_000_000


def load_benchmark_pricing(path: Path) -> BenchmarkPricingSpecification:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return BenchmarkPricingSpecification.model_validate(data)
    except (OSError, yaml.YAMLError, ValidationError) as exc:
        raise ValueError("invalid benchmark pricing specification") from exc
