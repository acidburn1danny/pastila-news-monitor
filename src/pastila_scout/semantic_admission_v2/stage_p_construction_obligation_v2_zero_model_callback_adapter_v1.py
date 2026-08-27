"""Zero-model projection adapter for synthetic token-piece verification."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .stage_p_construction_obligation_v2_projector_binding_v1 import (
    DECODER_IDENTITY, PROJECTOR_FREEZE_IDENTITY, TOKENIZER_IDENTITY,
    ConstructionObligationV2ProjectorSourceBindingV1,
    bind_construction_obligation_v2_projector_v1)
from .stage_p_construction_obligation_v2_runner_protocol_contract_v1 import RUNNER_PROTOCOL_IDENTITY
from .stage_p_construction_obligation_v2_token_projector_v1 import (
    StagePTokenProjectionFailureV1, TokenProjectionReceiptV1)


ADAPTER_IDENTITY = "b1d4a4932fb5365ede3a60d258046bd6523ed4e9029acbfe6a4ca99dac863c71"


@dataclass(frozen=True, slots=True)
class ZeroModelCallbackDecisionV1:
    allowed_token_ids: tuple[int, ...]
    projection_receipt: TokenProjectionReceiptV1
    no_legal_token_receipt: bytes | None


class ZeroModelCallbackFailureV1(RuntimeError):
    def __init__(self, receipt: TokenProjectionReceiptV1):
        super().__init__(receipt.reason_code or "ZERO_MODEL_CALLBACK_FAILURE")
        self.receipt = receipt


class ConstructionObligationV2ZeroModelCallbackAdapterV1:
    def __init__(self, *, source_binding: ConstructionObligationV2ProjectorSourceBindingV1,
                 token_pieces: Mapping[int, str]) -> None:
        self._source_binding = source_binding
        self._token_pieces = dict(token_pieces)
        self._incremental = bind_construction_obligation_v2_projector_v1(
            envelope=source_binding, token_pieces=self._token_pieces)
        self._previous: tuple[int, ...] = ()

    def project(self, *, generated_token_ids: Sequence[int],
                decode: Callable[[Sequence[int]], str]) -> ZeroModelCallbackDecisionV1:
        ids = _exact_ids(generated_token_ids)
        if ids[:len(self._previous)] != self._previous:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_PREFIX_NOT_INCREMENTAL")
        rebuilt = bind_construction_obligation_v2_projector_v1(
            envelope=self._source_binding, token_pieces=self._token_pieces)
        left = _project(self._incremental, ids, decode)
        right = _project(rebuilt, ids, decode)
        if _equivalence(left) != _equivalence(right):
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_REBUILD_DIVERGENCE")
        self._previous = ids
        result, failure = left
        if failure is not None:
            if failure.reason_code != "TOKENIZATION_DEAD_NO_VALID_TOKEN":
                raise ZeroModelCallbackFailureV1(failure)
            return ZeroModelCallbackDecisionV1((), failure, _no_legal_receipt(failure, ids))
        return ZeroModelCallbackDecisionV1(result.token_ids, result.receipt, None)


def _project(projector, ids, decode):
    try:
        return projector.allowed_token_ids(ids, decode), None
    except StagePTokenProjectionFailureV1 as exc:
        return None, exc.receipt


def _equivalence(value):
    result, failure = value
    receipt = result.receipt if result is not None else failure
    return ((result.token_ids if result is not None else ()), receipt.decoded_sha256,
            receipt.dfa_mode, receipt.terminal, receipt.legal_token_count,
            receipt.eos_allowed, receipt.reason_code)


def _exact_ids(value: Sequence[int]) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_TOKEN_IDS_INVALID")
    result = tuple(value)
    if any(type(item) is not int or item < 0 for item in result):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_TOKEN_IDS_INVALID")
    return result


def _no_legal_receipt(receipt: TokenProjectionReceiptV1, ids: tuple[int, ...]) -> bytes:
    prefix_sha = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode()).hexdigest()
    state_identity = hashlib.sha256("\n".join((receipt.request_context_identity,
        receipt.decoded_sha256, receipt.dfa_mode, str(receipt.terminal))).encode()).hexdigest()
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-no-legal-token-receipt",
        "schema_version": "1.0.0-evaluation.1", "protocol_identity": RUNNER_PROTOCOL_IDENTITY,
        "projector_freeze_identity": PROJECTOR_FREEZE_IDENTITY,
        "tokenizer_identity": TOKENIZER_IDENTITY, "decoder_identity": DECODER_IDENTITY,
        "provider_request_id": f"zero-model:{receipt.request_context_identity}",
        "source_context_identity": receipt.request_context_identity,
        "generated_prefix_sha256": prefix_sha, "generated_token_count": len(ids),
        "character_state_identity": state_identity, "dfa_mode": receipt.dfa_mode,
        "terminal": False, "allowed_token_count": 0,
        "failure_code": "NO_LEGAL_TOKEN_NONTERMINAL", "receipt_identity": ""}
    material = {key: item for key, item in value.items() if key != "receipt_identity"}
    value["receipt_identity"] = hashlib.sha256(_canonical(material)).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = ("ADAPTER_IDENTITY", "ConstructionObligationV2ZeroModelCallbackAdapterV1",
           "ZeroModelCallbackDecisionV1", "ZeroModelCallbackFailureV1")
