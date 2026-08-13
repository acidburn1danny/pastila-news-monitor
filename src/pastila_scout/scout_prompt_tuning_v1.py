"""Small Ollama-first evaluation loop for the production Scout prompt."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from pastila_scout.ai.editorial_scoring import EDITORIAL_SCORING_INSTRUCTIONS
from pastila_scout.application_request_authority_v1 import (
    ApplicationProviderRequestV1,
    ApplicationRequestAuthorityV1,
)
from pastila_scout.provider_execution_ollama_v1 import (
    OllamaExecutionConfigV1,
    OllamaHttpClientV1,
    OllamaProviderExecutorV1,
)
from pastila_scout.provider_execution_v2 import (
    CancellationTokenV2,
    ExecutionOutcomeV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.scout_cli_provider_run_v1.execution import execute_provider_run


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class TuningExpectedV1(_Model):
    relevant: bool
    category: str
    priority: str
    duplicate_group: str | None = None

    @field_validator("priority")
    @classmethod
    def priority_is_coarse(cls, value: str) -> str:
        if value not in {"high", "medium", "low"}:
            raise ValueError("unsupported priority")
        return value


class TuningCaseV1(_Model):
    id: str = Field(pattern=r"^case-[0-9]{3}$")
    title: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=2000)
    source: str = Field(min_length=1, max_length=200)
    expected: TuningExpectedV1


class TuningDatasetV1(_Model):
    name: str = Field(min_length=1)
    version: int = Field(ge=1)
    cases: tuple[TuningCaseV1, ...] = Field(min_length=1, max_length=100)

    @field_validator("cases")
    @classmethod
    def unique_cases(cls, value: tuple[TuningCaseV1, ...]):
        if len({item.id for item in value}) != len(value):
            raise ValueError("case IDs must be unique")
        return value


class TuningActualV1(_Model):
    id: str
    relevant: bool
    category: str
    priority: str
    duplicate_group: str | None = None

    _priority = field_validator("priority")(TuningExpectedV1.priority_is_coarse.__func__)


class TuningProviderOutputV1(_Model):
    cases: tuple[TuningActualV1, ...]


def load_tuning_dataset(path: Path) -> TuningDatasetV1:
    return TuningDatasetV1.model_validate_json(path.read_text(encoding="utf-8"))


def build_tuning_prompt(
    dataset: TuningDatasetV1, *, variant: str = "current", override: str | None = None
) -> str:
    schema = TuningProviderOutputV1.model_json_schema()
    cases = [
        {"id": item.id, "title": item.title, "summary": item.summary, "source": item.source}
        for item in dataset.cases
    ]
    addition = "" if override is None else f"\nCandidate prompt adjustment:\n{override.strip()}"
    return (
        f"{EDITORIAL_SCORING_INSTRUCTIONS}\n"
        "For each supplied case, decide relevance conservatively first, then return "
        "relevant boolean; category; priority high/medium/low; and duplicate_group. "
        "Category is mandatory and MUST be exactly one of: Politica, Social, "
        "Conspiratii, Economie, CanCan, Externe, Diverse. Copy exactly one value "
        "with this spelling and capitalization; never translate it, invent a "
        "synonym, use a free-form label, or return null. Assign the best-fit category "
        "even when relevant is false. Use Politica for government/law/public "
        "contracts, Social for public services/health/education/protests/accidents, "
        "Conspiratii for conspiracy claims, Economie for finance/business/employment, "
        "CanCan for celebrity/monden, Externe for international affairs, and Diverse "
        "for remaining material. Cases describing the same concrete event from "
        "different sources must receive the same non-null duplicate_group; unrelated "
        "cases must use null. Return JSON only.\n"
        f"Prompt variant: {variant}.{addition}\n"
        f"Cases: {json.dumps(cases, ensure_ascii=False, separators=(',', ':'))}\n"
        f"Required JSON schema: {json.dumps(schema, separators=(',', ':'))}"
    )


def evaluate_tuning_run(
    dataset: TuningDatasetV1, actual: TuningProviderOutputV1
) -> dict[str, object]:
    expected = {item.id: item.expected for item in dataset.cases}
    received = {item.id: item for item in actual.cases}
    if set(received) != set(expected) or len(received) != len(actual.cases):
        raise ValueError("provider result case identity mismatch")
    false_positives: list[str] = []
    false_negatives: list[str] = []
    category_matches = priority_matches = relevance_matches = 0
    mismatches: list[dict[str, object]] = []
    for case in dataset.cases:
        wanted, got = case.expected, received[case.id]
        relevance_matches += got.relevant == wanted.relevant
        category_matches += got.category == wanted.category
        priority_matches += got.priority == wanted.priority
        if got.relevant and not wanted.relevant:
            false_positives.append(case.id)
        if wanted.relevant and not got.relevant:
            false_negatives.append(case.id)
        differences = tuple(
            name
            for name in ("relevant", "category", "priority")
            if getattr(wanted, name) != getattr(got, name)
        )
        wanted_peers = {
            other.id
            for other in dataset.cases
            if other.id != case.id
            and wanted.duplicate_group is not None
            and other.expected.duplicate_group == wanted.duplicate_group
        }
        got_peers = {
            other.id
            for other in actual.cases
            if other.id != case.id
            and got.duplicate_group is not None
            and other.duplicate_group == got.duplicate_group
        }
        if wanted_peers != got_peers:
            differences += ("duplicate_group",)
        if differences:
            mismatches.append({"id": case.id, "fields": differences})
    count = len(dataset.cases)
    return {
        "cases": count,
        "relevance": {"correct": relevance_matches, "total": count},
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "category": {"correct": category_matches, "total": count},
        "duplicate": {
            "correct": count
            - sum("duplicate_group" in item["fields"] for item in mismatches),
            "total": count,
        },
        "priority": {"correct": priority_matches, "total": count},
        "mismatches": mismatches,
    }


def run_tuning(
    *,
    dataset: TuningDatasetV1,
    model: str,
    base_url: str,
    timeout: float,
    execute: Callable[[str], str],
    variant: str = "current",
    override: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, object]:
    prompt = build_tuning_prompt(dataset, variant=variant, override=override)
    parsed = TuningProviderOutputV1.model_validate_json(execute(prompt))
    dataset_bytes = json.dumps(
        dataset.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "timestamp": now().isoformat(),
        "provider": "ollama",
        "model": model,
        "base_url": base_url,
        "timeout_seconds": timeout,
        "prompt_variant": variant,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "metrics": evaluate_tuning_run(dataset, parsed),
        "results": parsed.model_dump(mode="json")["cases"],
    }


def execute_ollama_prompt(
    prompt: str, *, model: str, base_url: str, timeout: float
) -> str:
    requested_at = datetime.now(UTC)
    application = ApplicationProviderRequestV1(
        ProviderChoiceV1.OLLAMA,
        prompt,
        f"scout-tuning-v1:{hashlib.sha256(prompt.encode()).hexdigest()}",
        requested_at,
        TimeoutPolicyV2(timeout_seconds=timeout),
        CancellationTokenV2(cancellation_requested=False),
    )
    request = ApplicationRequestAuthorityV1().build(application)
    with httpx.Client() as http:
        executor = OllamaProviderExecutorV1(
            OllamaHttpClientV1(http),
            OllamaExecutionConfigV1(model=model, base_url=base_url),
        )
        result = execute_provider_run(
            provider=ProviderChoiceV1.OLLAMA,
            provider_request=request,
            selected_executor=executor,
        ).provider_result
    if result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None:
        raise RuntimeError(result.failure_code or "ollama-execution-failed")
    outputs = result.provider_result.outputs
    if len(outputs) != 1:
        raise RuntimeError("ollama-output-invalid")
    return outputs[0].generated_text


def save_tuning_result(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
