"""Candidate-neutral, offline technical-output envelope derivation primitives."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

TOP_LEVEL_FIELDS = (
    "schema",
    "schema_version",
    "case_id",
    "request_identity",
    "output_type",
    "outcome",
    "text",
    "claim_bindings",
    "abstention_code",
)
CLAIM_FIELDS = ("claim_index", "source_span_ids")
SOURCE_SPAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_SPAN_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
CASE_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
REQUEST_IDENTITY = re.compile(r"^sha256:[0-9a-f]{64}$")
ABSTENTION_CODES = frozenset(
    {
        "INSUFFICIENT_AUTHORITY",
        "CONFLICTING_AUTHORITY",
        "AMBIGUOUS_SCOPE",
        "UNRESOLVED_REFERENCE",
        "INSTRUCTION_AUTHORITY_CONFLICT",
        "CANNOT_SATISFY_OUTPUT_CONTRACT",
        "SAFETY_ENVELOPE_EXCEEDED",
    }
)
BRANCHES = frozenset(
    {"FACTUAL_ANSWER", "COMMENTARY_ANSWER", "FACTUAL_ABSTAIN", "COMMENTARY_ABSTAIN"}
)

TECHNICAL_BYTE_CEILING = 6268
TECHNICAL_TOKEN_CEILING = 6268
BYTE_CEILING_CLASSIFICATION = "EXACT_CANONICAL_MAXIMUM"
TOKEN_CEILING_CLASSIFICATION = "CONSERVATIVE_BYTE_TIGHT_TOKEN_CEILING"


class OfflineTokenizer(Protocol):
    identity: str

    def encode(self, text: str, *, add_special_tokens: bool) -> Sequence[int]: ...


@dataclass(frozen=True)
class FiniteResponseSpace:
    """A closed finite space supplied by a trusted, separately qualified builder."""

    identity: str
    responses: tuple[Mapping[str, object], ...]
    covered_branches: frozenset[str]

    def __post_init__(self) -> None:
        if not self.identity or not self.responses or self.covered_branches != BRANCHES:
            raise ValueError("response space is not a complete qualified finite fixture")
        actual_branches: set[str] = set()
        for response in self.responses:
            canonical_response_bytes(response)
            output_type = response.get("output_type")
            outcome = response.get("outcome")
            branch = f"{output_type}_{outcome}"
            if branch not in BRANCHES:
                raise ValueError("response space contains an invalid branch")
            actual_branches.add(branch)
        if actual_branches != BRANCHES:
            raise ValueError("response bytes do not cover every contract branch")


def _normalize(value: object) -> object:
    if isinstance(value, str):
        if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
            raise ValueError("unpaired surrogate prohibited")
        normalized = unicodedata.normalize("NFC", value)
        if any(ord(character) < 0x20 for character in normalized):
            raise ValueError("control character prohibited")
        return normalized
    if value is None:
        return None
    if type(value) is int:
        return value
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _normalize(item) for key, item in value.items()}
    raise ValueError("unsupported canonical JSON value")


def _validate_ordered_response(response: Mapping[str, object]) -> None:
    if tuple(response) != TOP_LEVEL_FIELDS:
        raise ValueError("non-contractual top-level field order")
    claims = response["claim_bindings"]
    if not isinstance(claims, list):
        raise TypeError("claim_bindings must be an array")
    if len(claims) > 3:
        raise ValueError("too many claim bindings")
    all_span_ids: list[str] = []
    for expected_index, claim in enumerate(claims, start=1):
        if not isinstance(claim, Mapping) or tuple(claim) != CLAIM_FIELDS:
            raise ValueError("non-contractual claim field order")
        if type(claim["claim_index"]) is not int:
            raise ValueError("claim_index must be an integer")
        if claim["claim_index"] != expected_index:
            raise ValueError("claim indexes must be contiguous")
        span_ids = claim["source_span_ids"]
        if not isinstance(span_ids, list):
            raise TypeError("source_span_ids must be an array")
        if not 1 <= len(span_ids) <= 8:
            raise ValueError("source_span_ids cardinality invalid")
        for span_id in span_ids:
            if not isinstance(span_id, str) or SOURCE_SPAN_ID.fullmatch(span_id) is None:
                raise ValueError("invalid source_span_id")
            if span_id.startswith("sha256:") and SHA256_SPAN_ID.fullmatch(span_id) is None:
                raise ValueError("noncanonical sha256 source_span_id")
            all_span_ids.append(span_id)
    if len(all_span_ids) > 24 or len(all_span_ids) != len(set(all_span_ids)):
        raise ValueError("aggregate source_span_ids invalid")

    if response["schema"] != "pastila-core-v2-structured-qualification-response":
        raise ValueError("schema mismatch")
    if type(response["schema_version"]) is not int or response["schema_version"] != 1:
        raise ValueError("schema_version mismatch")
    case_id = response["case_id"]
    request_identity = response["request_identity"]
    if not isinstance(case_id, str) or CASE_ID.fullmatch(case_id) is None:
        raise ValueError("case_id invalid")
    if not isinstance(request_identity, str) or REQUEST_IDENTITY.fullmatch(request_identity) is None:
        raise ValueError("request_identity invalid")
    output_type = response["output_type"]
    outcome = response["outcome"]
    text = response["text"]
    abstention_code = response["abstention_code"]
    if output_type not in {"FACTUAL", "COMMENTARY"} or outcome not in {"ANSWER", "ABSTAIN"}:
        raise ValueError("output branch invalid")
    if outcome == "ABSTAIN":
        if text is not None or claims or abstention_code not in ABSTENTION_CODES:
            raise ValueError("abstention invariant invalid")
        return
    if not isinstance(text, str) or not text or abstention_code is not None:
        raise ValueError("answer invariant invalid")
    normalized_length = len(unicodedata.normalize("NFC", text))
    if output_type == "FACTUAL":
        if not claims or normalized_length > 650:
            raise ValueError("factual answer invariant invalid")
    elif claims or normalized_length > 1000:
        raise ValueError("commentary answer invariant invalid")


def canonical_response_bytes(response: Mapping[str, object]) -> bytes:
    """Return the one approved compact UTF-8 representation, without BOM/newline."""

    _validate_ordered_response(response)
    normalized = _normalize(response)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8", errors="strict")


def maximal_structural_response() -> dict[str, object]:
    """Return the attaining witness for the approved conservative lexical superset."""

    span_ids = ["s" + ("z" * 124) + f"{index:03d}" for index in range(24)]
    return {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 1,
        "case_id": "c" + ("z" * 127),
        "request_identity": "sha256:" + ("f" * 64),
        "output_type": "FACTUAL",
        "outcome": "ANSWER",
        "text": "\U0010ffff" * 650,
        "claim_bindings": [
            {"claim_index": index + 1, "source_span_ids": span_ids[index * 8 : (index + 1) * 8]}
            for index in range(3)
        ],
        "abstention_code": None,
    }


def structural_branch_byte_maxima() -> dict[str, int]:
    """Derive an attaining canonical-byte maximum for every contract branch."""

    factual = maximal_structural_response()
    commentary = {
        **factual,
        "output_type": "COMMENTARY",
        "text": "\U0010ffff" * 1000,
        "claim_bindings": [],
    }
    longest_abstention = max(ABSTENTION_CODES, key=lambda value: (len(value), value))
    abstentions = {
        output_type: {
            **factual,
            "output_type": output_type,
            "outcome": "ABSTAIN",
            "text": None,
            "claim_bindings": [],
            "abstention_code": longest_abstention,
        }
        for output_type in ("FACTUAL", "COMMENTARY")
    }
    witnesses = {
        "FACTUAL_ANSWER": factual,
        "COMMENTARY_ANSWER": commentary,
        "FACTUAL_ABSTAIN": abstentions["FACTUAL"],
        "COMMENTARY_ABSTAIN": abstentions["COMMENTARY"],
    }
    return {name: len(canonical_response_bytes(value)) for name, value in witnesses.items()}


def derive_approved_production_envelope(*, tokenizer_byte_tight_proven: bool) -> dict[str, object]:
    """Emit the owner-approved safety envelope only after its proof gate closes."""

    witness = canonical_response_bytes(maximal_structural_response())
    branch_maxima = structural_branch_byte_maxima()
    if len(witness) != TECHNICAL_BYTE_CEILING:
        raise RuntimeError("canonical maximum witness identity changed")
    if max(branch_maxima.values()) != TECHNICAL_BYTE_CEILING:
        raise RuntimeError("structural branch maximum changed")
    if not tokenizer_byte_tight_proven:
        raise ValueError("tokenizer tokens<=bytes closure is not proven")
    return {
        "technical_byte_ceiling": TECHNICAL_BYTE_CEILING,
        "technical_byte_ceiling_classification": BYTE_CEILING_CLASSIFICATION,
        "technical_token_ceiling": TECHNICAL_TOKEN_CEILING,
        "technical_token_ceiling_classification": TOKEN_CEILING_CLASSIFICATION,
        "byte_witness_sha256": hashlib.sha256(witness).hexdigest(),
        "structural_branch_byte_maxima": branch_maxima,
        "tokenizer_exact_maximum_claimed": False,
        "formal_bpe_maximizer_authorized": False,
        "margin_bytes": 0,
        "margin_tokens": 0,
        "candidate_derived": False,
        "overflow_behavior": "FAIL_CLOSED",
        "truncation": "PROHIBITED",
        "retry_or_redraw": "PROHIBITED",
        "semantic_quality_effect": "NONE",
    }


def enforce_technical_output_envelope(
    response: Mapping[str, object], tokenizer: OfflineTokenizer
) -> bytes:
    """Fail closed before acceptance when either approved safety ceiling is exceeded."""

    canonical_bytes = canonical_response_bytes(response)
    token_ids = tuple(
        tokenizer.encode(
            canonical_bytes.decode("utf-8", errors="strict"), add_special_tokens=False
        )
    )
    if len(canonical_bytes) > TECHNICAL_BYTE_CEILING:
        raise ValueError("technical byte ceiling exceeded")
    if len(token_ids) > TECHNICAL_TOKEN_CEILING:
        raise ValueError("technical token ceiling exceeded")
    return canonical_bytes


def derive_synthetic_envelope(
    space: FiniteResponseSpace,
    tokenizer: OfflineTokenizer,
    *,
    tokenizer_closure_validator: Callable[[OfflineTokenizer], bool],
) -> dict[str, object]:
    """Qualify the mechanism on a closed synthetic space; never emit production authority."""

    if not tokenizer.identity or not tokenizer_closure_validator(tokenizer):
        raise ValueError("tokenizer closure is not qualified offline")
    observations: list[tuple[int, int, str, bytes]] = []
    space_hasher = hashlib.sha256()
    for response in space.responses:
        encoded = canonical_response_bytes(response)
        space_hasher.update(len(encoded).to_bytes(8, byteorder="big"))
        space_hasher.update(encoded)
        token_count = len(
            tuple(
                tokenizer.encode(
                    encoded.decode("utf-8", errors="strict"), add_special_tokens=False
                )
            )
        )
        if token_count < 0:
            raise ValueError("invalid tokenizer result")
        observations.append(
            (len(encoded), token_count, hashlib.sha256(encoded).hexdigest(), encoded)
        )
    byte_witness = max(observations, key=lambda item: (item[0], item[2]))
    token_witness = max(observations, key=lambda item: (item[1], item[2]))
    receipt = {
        "schema": "pastila-production-core-synthetic-technical-output-envelope-receipt",
        "schema_version": 1,
        "status": "PASS_SYNTHETIC_MECHANISM_ONLY_NO_PRODUCTION_AUTHORITY",
        "space_identity": space.identity,
        "response_space_sha256": space_hasher.hexdigest(),
        "tokenizer_identity": tokenizer.identity,
        "response_count": len(space.responses),
        "byte_maximum": byte_witness[0],
        "byte_witness_sha256": byte_witness[2],
        "token_exact_maximum": token_witness[1],
        "token_witness_sha256": token_witness[2],
        "production_value_authority": False,
        "candidate_model_executed": False,
        "candidate_result_inspected": False,
    }
    receipt_bytes = json.dumps(
        receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {**receipt, "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest()}


def qualified_finite_space(
    responses: Iterable[Mapping[str, object]], *, identity: str, covered_branches: Iterable[str]
) -> FiniteResponseSpace:
    return FiniteResponseSpace(identity, tuple(responses), frozenset(covered_branches))
