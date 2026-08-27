"""Bounded model realization for the numeric threshold Voice program.

The model may author only an explicitly nonfactual comic passage.  Factual prose
remains owned by Semantic Draft V2 and is never included in the returned text.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity

PROGRAM_ID = "NEL_CATEGORY_THRESHOLD_RECLASSIFICATION_V1"
REALIZER_IDENTITY = "pastilaacida-voice:governed-nonfactual-realizer:v1"
MODEL_ID = "pastila-editor-core-v1.2-experimental"
_TRUNCATION = re.compile(r"\[(?:\s*)?(?:\.{3}|…)(?:\s*)?\]|\b(?:etc\.)$", re.IGNORECASE)
_NUMBER = re.compile(r"(?<!\w)\d|\b(?:lei|euro|dolari|procente|milioane|miliarde)\b", re.IGNORECASE)
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_SENSITIVE_SURFACE = re.compile(
    r"\b(?:cadavr\w*|deced\w*|mort\w*|captivit\w*|ostatic\w*|răpi\w*|"
    r"arestat\w*|acuza\w*|incendiu\w*|dron\w*|militar\w*|nato)\b",
    re.IGNORECASE,
)
_INVENTED_SPEECH = re.compile(
    r"[«»„”\"]|\b(?:a zis|a spus|a răspuns|ar fi spus|le-a spus|i-a spus)\b",
    re.IGNORECASE,
)
_UNSUPPORTED_MENTAL_OR_CAUSAL = re.compile(
    r"\b(?:a decis|au decis|vrea să|voia să|gândindu-se|pentru că|ca să|"
    r"spune|spunând|regizor\w* spune)\b",
    re.IGNORECASE,
)
_REAL_WORLD_FACTUAL_RETURN = re.compile(
    r"\b(?:aici (?:nu )?e vorba de|în realitate|oameni care|nu au primit|"
    r"nu a fost doar|a plătit pentru)\b",
    re.IGNORECASE,
)
_OPENING_ATTRACTOR = re.compile(r"^Dacă\b", re.IGNORECASE)
_ABSTENTION_REASONS = {
    "SERIOUS_OR_SENSITIVE_SURFACE",
    "CANNOT_AVOID_FACTUAL_CLAIMS",
    "NO_SAFE_COMIC_ANGLE",
}

PROMPT_TEMPLATE = """AUTORITATE VOICE LIMITATĂ — NUMAI COMENTARIU NONFACTUAL

Rezumatul factual de mai jos este context imuabil. Nu îl repeta, nu îl
parafraza și nu adăuga afirmații factuale, nume, cifre, date sau atribuiri.

Pentru moarte, captivitate, acuzații sau arestări, incendii ori operațiuni
militare, alege abstention. Nu inventa dialog, intenții, cauze, decizii,
consecințe sau cunoștințe despre rolurile persoanelor reale.

Scrie un singur pasaj oral, natural, de 1-4 propoziții, în română. Alege liber
dacă umorul este potrivit și nu folosi automat aceeași formulă de deschidere.
Dacă inventezi o analogie sau o scenă, marcheaz-o explicit ca imaginară chiar
în formularea locală, fără a o prezenta drept fapt. Încheie precis. Fără titlu,
liste, fragmente izolate, paranteze de trunchiere sau text factual.
Primul cuvânt nu poate fi „Dacă”. Nu folosi comparația ipotetică drept schelet
automat și nu reveni apoi la afirmații despre lumea reală.

Răspunde cu exact un singur obiect JSON, pe un singur rând, fără Markdown,
fără ``` și fără text înainte sau după. Sunt permise numai aceste forme:
{{"decision":"commentary","commentary":"..."}}
{{"decision":"abstain","reason_code":"SERIOUS_OR_SENSITIVE_SURFACE"}}
Pentru abstention mai sunt permise reason_code CANNOT_AVOID_FACTUAL_CLAIMS sau
NO_SAFE_COMIC_ANGLE. Nu combina formele și nu adăuga alte chei.

REZUMAT FACTUAL IMUABIL:
{factual_summary}"""
PROMPT_IDENTITY = "sha256:" + hashlib.sha256(PROMPT_TEMPLATE.encode()).hexdigest()


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GovernedRealizationReceiptV1(_Frozen):
    schema_name: str = "pastilaacida-governed-nonfactual-realization"
    schema_version: str = "1"
    program_id: str
    realizer_identity: str = REALIZER_IDENTITY
    model_identity: str
    prompt_identity: str = PROMPT_IDENTITY
    factual_summary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    commentary_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_codes: tuple[str, ...]
    receipt_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class GovernedRealizationOutcomeV1:
    commentary: str | None
    receipt: GovernedRealizationReceiptV1 | None
    reason_code: str | None
    model_calls: int
    provider_calls: int
    model_loads: int


class GovernedNumericRealizerV1:
    def __init__(self, generate: Callable[[str], tuple[str, str]]) -> None:
        self._generate = generate

    def realize(self, *, program_id: str, factual_summary: str):
        if program_id != PROGRAM_ID:
            return GovernedRealizationOutcomeV1(
                None, None, "governed_realizer_program_not_authorized", 0, 0, 0
            )
        if not _clean_summary(factual_summary):
            return GovernedRealizationOutcomeV1(
                None, None, "governed_realizer_invalid_factual_context", 0, 0, 0
            )
        if _SENSITIVE_SURFACE.search(factual_summary):
            receipt = _receipt(
                program_id,
                factual_summary,
                "",
                "",
                MODEL_ID,
                ("policy_abstention", "SERIOUS_OR_SENSITIVE_SURFACE"),
            )
            return GovernedRealizationOutcomeV1(
                None,
                receipt,
                "governed_realizer_abstained:SERIOUS_OR_SENSITIVE_SURFACE",
                0,
                0,
                0,
            )
        prompt = PROMPT_TEMPLATE.format(factual_summary=factual_summary)
        try:
            raw, model_identity = self._generate(prompt)
        except Exception:  # noqa: BLE001 - provider failures always abstain
            receipt = _receipt(
                program_id, factual_summary, "", "", MODEL_ID, ("provider_failure",)
            )
            return GovernedRealizationOutcomeV1(
                None, receipt, "governed_realizer_provider_failure", 1, 1, 1
            )
        parsed = _parse(raw)
        if parsed is None:
            receipt = _receipt(
                program_id, factual_summary, raw, "", model_identity, ("invalid_json",)
            )
            return GovernedRealizationOutcomeV1(
                None, receipt, "governed_realizer_validation_failed:invalid_json", 1, 1, 1
            )
        decision, commentary, abstention_reason = parsed
        if decision == "abstain":
            assert abstention_reason is not None
            receipt = _receipt(
                program_id,
                factual_summary,
                raw,
                "",
                model_identity,
                ("governed_abstention", abstention_reason),
            )
            return GovernedRealizationOutcomeV1(
                None,
                receipt,
                "governed_realizer_abstained:" + abstention_reason,
                1,
                1,
                1,
            )
        codes = _validate(commentary, factual_summary)
        if codes:
            receipt = _receipt(
                program_id,
                factual_summary,
                raw,
                commentary or "",
                model_identity,
                codes,
            )
            return GovernedRealizationOutcomeV1(
                None,
                receipt,
                "governed_realizer_validation_failed:" + ",".join(codes),
                1,
                1,
                1,
            )
        assert commentary is not None
        receipt = _receipt(
            program_id,
            factual_summary,
            raw,
            commentary,
            model_identity,
            ("exact_commentary_contract", "no_factual_overlap"),
        )
        return GovernedRealizationOutcomeV1(commentary, receipt, None, 1, 1, 1)


def _receipt(program_id, summary, raw, commentary, model_identity, codes):
    payload = {
            "schema_name": "pastilaacida-governed-nonfactual-realization",
            "schema_version": "1",
            "program_id": program_id,
            "realizer_identity": REALIZER_IDENTITY,
            "model_identity": model_identity,
            "prompt_identity": PROMPT_IDENTITY,
            "factual_summary_sha256": _sha(summary),
            "raw_response_sha256": _sha(raw),
            "commentary_sha256": _sha(commentary),
            "validation_codes": tuple(codes),
            "receipt_identity": "sha256:" + "0" * 64,
        }
    payload["receipt_identity"] = canonical_identity(payload)
    return GovernedRealizationReceiptV1(**payload)


def build_core_v1_2_generator(*, executor, timeout_seconds: float):
    """Adapt the already configured local Core executor to the bounded realizer."""

    from datetime import UTC, datetime

    from pastila_scout.application_request_authority_v1 import (
        ApplicationProviderRequestV1,
        ApplicationRequestAuthorityV1,
    )
    from pastila_scout.provider_execution_v2 import (
        CancellationTokenV2,
        ExecutionOutcomeV2,
        TimeoutPolicyV2,
    )
    from pastila_scout.provider_selection_v1 import ProviderChoiceV1
    from pastila_scout.provider_v2 import (
        ProviderFinishReasonV2,
        ProviderResultStatusV2,
    )

    def generate(prompt: str) -> tuple[str, str]:
        authority = ApplicationRequestAuthorityV1().build(
            ApplicationProviderRequestV1(
                ProviderChoiceV1.OLLAMA,
                prompt,
                "voice-governed-realization:" + _sha(prompt)[:32],
                datetime.now(UTC),
                TimeoutPolicyV2(timeout_seconds=timeout_seconds),
                CancellationTokenV2(cancellation_requested=False),
            )
        )
        result = executor.execute(authority)
        if (
            result.outcome is not ExecutionOutcomeV2.COMPLETED
            or result.provider_result is None
            or result.provider_result.status is not ProviderResultStatusV2.SUCCESS
            or len(result.provider_result.outputs) != 1
            or result.provider_result.outputs[0].finish_reason
            is not ProviderFinishReasonV2.COMPLETED
        ):
            raise RuntimeError("local Voice realization failed")
        return result.provider_result.outputs[0].generated_text, MODEL_ID

    return generate


def _parse(raw: str) -> tuple[str, str | None, str | None] | None:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if type(value) is not dict:
        return None
    if set(value) == {"decision", "commentary"} and value["decision"] == "commentary":
        text = value["commentary"]
        return ("commentary", text, None) if type(text) is str else None
    if set(value) == {"decision", "reason_code"} and value["decision"] == "abstain":
        reason = value["reason_code"]
        if type(reason) is str and reason in _ABSTENTION_REASONS:
            return "abstain", None, reason
    return None


def _validate(commentary: str | None, summary: str) -> tuple[str, ...]:
    if commentary is None:
        return ("invalid_json",)
    codes: list[str] = []
    if _SENSITIVE_SURFACE.search(summary):
        codes.append("sensitive_surface_requires_abstention")
    if commentary != commentary.strip() or not 40 <= len(commentary) <= 600:
        codes.append("invalid_length_or_padding")
    if _TRUNCATION.search(commentary):
        codes.append("truncation_artifact")
    if _NUMBER.search(commentary):
        codes.append("factual_quantity_or_currency")
    if _INVENTED_SPEECH.search(commentary):
        codes.append("invented_quotation_or_role_knowledge")
    if _UNSUPPORTED_MENTAL_OR_CAUSAL.search(commentary):
        codes.append("unsupported_causality_intent_or_status")
    if _REAL_WORLD_FACTUAL_RETURN.search(commentary):
        codes.append("fiction_returns_as_unsupported_fact")
    if _OPENING_ATTRACTOR.search(commentary):
        codes.append("repeated_opening_attractor")
    if commentary[-1:] not in ".!?":
        codes.append("incomplete_ending")
    if not 1 <= len(re.findall(r"[.!?]+(?:\s|$)", commentary)) <= 4:
        codes.append("invalid_spoken_sentence_count")
    summary_words = _normalized_words(summary)
    commentary_words = _normalized_words(commentary)
    summary_ngrams = {tuple(summary_words[i : i + 4]) for i in range(len(summary_words) - 3)}
    commentary_ngrams = {
        tuple(commentary_words[i : i + 4])
        for i in range(len(commentary_words) - 3)
    }
    if summary_ngrams.intersection(commentary_ngrams):
        codes.append("factual_paraphrase_overlap")
    entities = {
        word.casefold()
        for word in _WORD.findall(summary)
        if len(word) >= 4 and word[:1].isupper()
    }
    if entities.intersection(commentary_words):
        codes.append("factual_entity_reuse")
    return tuple(codes)


def _clean_summary(value: str) -> bool:
    return (
        type(value) is str
        and value == value.strip()
        and 20 <= len(value) <= 2_000
        and not _TRUNCATION.search(value)
    )


def _normalized_words(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", value.casefold())
    return [word for word in _WORD.findall(normalized) if len(word) > 2]


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = (
    "PROGRAM_ID",
    "PROMPT_IDENTITY",
    "REALIZER_IDENTITY",
    "GovernedNumericRealizerV1",
    "GovernedRealizationOutcomeV1",
    "GovernedRealizationReceiptV1",
    "build_core_v1_2_generator",
)
