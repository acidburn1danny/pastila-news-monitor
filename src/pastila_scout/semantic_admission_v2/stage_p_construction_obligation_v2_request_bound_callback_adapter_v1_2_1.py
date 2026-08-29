"""Authority-bound optimized V1.2.1 callback; V1 remains the static oracle."""
from __future__ import annotations
import hashlib
import json
from collections.abc import Mapping, Sequence

from .stage_p_construction_obligation_v2_generated_suffix_callback_v1 import (
    RequestBoundGeneratedSuffixCallbackV1)
from .stage_p_construction_obligation_v2_projector_binding_v1 import (
    DECODER_IDENTITY, PROJECTOR_FREEZE_IDENTITY, TOKENIZER_IDENTITY,
    ConstructionObligationV2ProjectorSourceBindingV1,
    bind_construction_obligation_v2_projector_v1)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import RunnerRequestV1
from .stage_p_construction_obligation_v2_runner_protocol_contract_v1 import (
    RUNNER_PROTOCOL_IDENTITY)
from .stage_p_construction_obligation_v2_token_projector_v1 import (
    StagePTokenProjectionFailureV1)
from .stage_p_construction_obligation_v2_token_projector_v2 import (
    StagePConstructionObligationV2TokenProjectorV2)
from .stage_p_construction_obligation_semantic_completeness_v1 import (
    SemanticCompletenessAdmissionV1, SemanticCompletenessPolicyV1)
from .immutable_source_span_reference_v1 import SourceRoleV1
from .stage_p_construction_obligation_v2_projector_binding_v1 import _decode_bound_source
from .stage_p_construction_obligation_v2_zero_model_callback_adapter_v1 import (
    ZeroModelCallbackDecisionV1)

ADAPTER_VERSION = "REQUEST_BOUND_OPTIMIZED_PROJECTOR_CALLBACK_V1_2_1"


class ConstructionObligationV2RequestBoundCallbackAdapterV1_2_1:
    def __init__(self, *, request: RunnerRequestV1,
                 source_binding: ConstructionObligationV2ProjectorSourceBindingV1,
                 token_pieces: Mapping[int, str], eos_token_id: int,
                 excluded_token_ids: Sequence[int], authority_receipt_identity: str,
                 prompt_token_ids: Sequence[int],
                 initial_token_pieces: Mapping[int, str] | None = None) -> None:
        if type(request) is not RunnerRequestV1:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_EXACT_TYPE_REQUIRED")
        if type(source_binding) is not ConstructionObligationV2ProjectorSourceBindingV1:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_SOURCE_BINDING_EXACT_TYPE_REQUIRED")
        if request.source_context_identity != source_binding.source_context_identity:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_REQUEST_CONTEXT_MISMATCH")
        if len(authority_receipt_identity) != 64:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_AUTHORITY_IDENTITY_INVALID")
        self.request = request
        self.authority_receipt_identity = authority_receipt_identity
        oracle = bind_construction_obligation_v2_projector_v1(
            envelope=source_binding, token_pieces=token_pieces)
        candidate = _decode_bound_source(
            source_binding.candidate_utf8_base64, source_binding.candidate_sha256,
            SourceRoleV1.CANDIDATE)
        factual_authority = _decode_bound_source(
            source_binding.factual_authority_utf8_base64,
            source_binding.factual_authority_sha256, SourceRoleV1.FACTUAL_AUTHORITY)
        completeness = SemanticCompletenessAdmissionV1(
            SemanticCompletenessPolicyV1.bind(
                candidate=candidate, factual_authority=factual_authority))
        self.projector = StagePConstructionObligationV2TokenProjectorV2(
            controller=oracle.controller,
            token_pieces=token_pieces, eos_token_id=eos_token_id,
            tokenizer_identity=TOKENIZER_IDENTITY, decoder_identity=DECODER_IDENTITY,
            request_context_identity=request.source_context_identity,
            request_authority_identity=authority_receipt_identity,
            excluded_token_ids=excluded_token_ids,
            initial_token_pieces=initial_token_pieces,
            terminal_admission=completeness.validate_terminal,
            terminal_admission_identity=completeness.policy.identity)
        self._suffix = RequestBoundGeneratedSuffixCallbackV1(
            request_identity=request.provider_request_id,
            prompt_token_ids=prompt_token_ids, project=self._project)
        self._suffix.validate_prompt_once(
            request_identity=request.provider_request_id,
            prompt_token_ids=prompt_token_ids)

    def project_generated_suffix(
        self, *, generated_token_ids: Sequence[int],
    ) -> ZeroModelCallbackDecisionV1:
        result = self._suffix.project_generated_suffix(
            request_identity=self.request.provider_request_id,
            generated_token_ids=generated_token_ids)
        if type(result) is not ZeroModelCallbackDecisionV1:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_OPTIMIZED_DECISION_EXACT_TYPE_REQUIRED")
        return result

    def _project(self, generated: Sequence[int]) -> ZeroModelCallbackDecisionV1:
        pieces = self.projector.token_pieces if hasattr(self.projector, "token_pieces") else None
        del pieces
        decode = lambda ids: _decode(self.projector, ids)
        try:
            projected = self.projector.allowed_token_ids(generated, decode)
            return ZeroModelCallbackDecisionV1(
                projected.token_ids, projected.receipt, None)
        except StagePTokenProjectionFailureV1 as exc:
            return ZeroModelCallbackDecisionV1(
                (), exc.receipt, _no_legal_receipt(
                    request=self.request, authority=self.authority_receipt_identity,
                    generated=generated, receipt=exc.receipt))


def _decode(projector, generated: Sequence[int]) -> str:
    # The immutable trie owns all token pieces but does not expose mutable runtime state.
    pieces = getattr(projector, "_bound_token_pieces", None)
    if pieces is None:
        raise RuntimeError("OPTIMIZED_PROJECTOR_TOKEN_PIECES_NOT_BOUND")
    try:
        if not generated:
            return ""
        initial = getattr(projector, "_bound_initial_token_pieces", pieces)
        return initial[generated[0]] + "".join(
            pieces[item] for item in generated[1:])
    except KeyError as exc:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATED_TOKEN_UNKNOWN") from exc


def _no_legal_receipt(*, request, authority, generated, receipt) -> bytes:
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-no-legal-token-receipt",
        "schema_version": "1.0.0-evaluation.1",
        "protocol_identity": RUNNER_PROTOCOL_IDENTITY,
        "projector_freeze_identity": PROJECTOR_FREEZE_IDENTITY,
        "tokenizer_identity": TOKENIZER_IDENTITY,
        "decoder_identity": DECODER_IDENTITY,
        "provider_request_id": request.provider_request_id,
        "source_context_identity": request.source_context_identity,
        "generated_prefix_sha256": hashlib.sha256(
            json.dumps(tuple(generated), separators=(",", ":")).encode()).hexdigest(),
        "generated_token_count": len(tuple(generated)),
        "character_state_identity": hashlib.sha256("\n".join((
            authority, receipt.request_context_identity, receipt.decoded_sha256,
            receipt.dfa_mode, str(receipt.terminal))).encode()).hexdigest(),
        "dfa_mode": receipt.dfa_mode, "terminal": False,
        "allowed_token_count": 0, "failure_code": "NO_LEGAL_TOKEN_NONTERMINAL",
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical(
        {k: v for k, v in value.items() if k != "receipt_identity"})).hexdigest()
    return _canonical(value)


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = ("ADAPTER_VERSION",
           "ConstructionObligationV2RequestBoundCallbackAdapterV1_2_1")
