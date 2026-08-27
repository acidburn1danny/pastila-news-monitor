"""Phases 0-7 tokenizer-only audit for the frozen Phase 2 character languages.

Evidence tooling only: it creates no projector, loads no model weights, and
performs no generation, provider, evaluator, runner, or probe operation.
"""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import time
from pathlib import Path


MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
EXPECTED_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
EXPECTED_VOCABULARY = 131072
PLAN_IDENTITY = "2cab0e835997349c010ef87b9f3682adb4b4f38b103b8a227d8a29ed8388ed67"
DECODER_IDENTITY = hashlib.sha256(
    b"TOKENIZERS_BACKEND_DECODE_SKIP_SPECIAL_TRUE_CLEANUP_FALSE_V1"
).hexdigest()


def _decode(tokenizer, ids) -> str:
    return tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)


def _identity(size: int) -> str:
    return "sha256:" + hashlib.sha256(f"{MODEL}\n{size}".encode()).hexdigest()


def _context():
    from .immutable_source_span_reference_v1 import ImmutableUtf8SourceV1, SourceRoleV1
    from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1
    return SourceReferenceConstraintContextV1.bind(
        candidate=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data="candidat ă pentru audit".encode()),
        factual_authority=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY,
            data=("autoritate înghețată " + "x" * 96).encode()),
    )


def _texts(context):
    from .stage_p_source_reference_constraint_v1 import (
        ReferenceFieldV1, canonical_reference_json_v1,
    )
    commitment = (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-commitment-span-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"COMMITMENT_SPAN_AUDIT","records":['
        '{"entry_id":"P1","decision":"SPAN_SUPPORTS_COMPLETE_COMMITMENT",'
        '"assertion_checked":true,"presupposition_checked":true,'
        '"entailment_checked":true,"necessary_implication_checked":true,'
        '"reason_code":null,"basis":"verificat ă"}]}'
    )
    support = canonical_reference_json_v1(
        context=context, field=ReferenceFieldV1.AUTHORITY_SUPPORT,
        start_utf8=0, end_utf8=context.factual_authority.byte_length)
    authority_supported = (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"AUTHORITY_RECONCILIATION_AUDIT","records":['
        '{"entry_id":"P1","full_authority_compared":true,"decision":"GOVERNED_SUPPORTED",'
        '"authority_support_ref":' + support + ',"event_axis":"MATCH",'
        '"modality_axis":"MATCH","timing_axis":"MATCH",'
        '"unsupported_finding_ids":[],"basis":"verificat"}],"unsupported_findings":[]}'
    )
    candidate = canonical_reference_json_v1(
        context=context, field=ReferenceFieldV1.CANDIDATE_SPAN,
        start_utf8=0, end_utf8=1)
    authority_unsupported = (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"AUTHORITY_RECONCILIATION_AUDIT","records":['
        '{"entry_id":"P1","full_authority_compared":true,'
        '"decision":"UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION",'
        '"authority_support_ref":null,"event_axis":"MATCH",'
        '"modality_axis":"MUTATION","timing_axis":"MATCH",'
        '"unsupported_finding_ids":["F1"],"basis":"verificat"}],'
        '"unsupported_findings":[{"finding_id":"F1","entry_id":"P1",'
        '"candidate_proposition_ref":' + candidate + ','
        '"reason_code":"FSEM_UNSUPPORTED_CAUSALITY","reason_status":"DECISIVE",'
        '"basis":"verificat"}]}'
    )
    second_finding = (
        '{"finding_id":"F2","entry_id":"P1","candidate_proposition_ref":' + candidate + ','
        '"reason_code":"FSEM_UNSUPPORTED_OUTCOME_OR_STATUS","reason_status":"DECISIVE",'
        '"basis":"verificat"}'
    )
    first_supporting = (
        '{"finding_id":"F1","entry_id":"P1","candidate_proposition_ref":' + candidate + ','
        '"reason_code":"FSEM_UNSUPPORTED_CAUSALITY","reason_status":"SUPPORTING",'
        '"basis":"verificat"}'
    )
    authority_two_findings = authority_unsupported.replace(
        '"unsupported_finding_ids":["F1"]',
        '"unsupported_finding_ids":["F1","F2"]',
    ).replace(
        authority_unsupported[authority_unsupported.index('{"finding_id":"F1"'):-2],
        first_supporting + "," + second_finding,
    )
    return commitment, authority_supported, authority_unsupported, authority_two_findings


def _prefix(text: str, marker: str, *, after: bool = True) -> str:
    position = text.index(marker) + (len(marker) if after else 0)
    return text[:position]


def _prefix_nth(text: str, marker: str, occurrence: int) -> str:
    position = -1
    for _ in range(occurrence):
        position = text.index(marker, position + 1)
    return text[:position + len(marker)]


def _matrix(context, texts):
    from .stage_p_phase2_character_dfa_v1 import (
        AuthorityReconciliationCharacterDfaV1 as Authority,
        CommitmentSpanAuditCharacterDfaV1 as Commitment,
    )
    commitment, supported, unsupported, two_findings = texts
    commitment_factory = lambda: Commitment.for_entries(("P1",))
    authority_factory = lambda: Authority.for_request(entry_ids=("P1",), context=context)
    rows = [
        ("COMMITMENT_INITIAL", commitment_factory, ""),
        ("COMMITMENT_LITERAL", commitment_factory, commitment[:1]),
        ("COMMITMENT_DECISION", commitment_factory, _prefix(commitment, '"decision":"')),
        ("COMMITMENT_STRING_EMPTY", commitment_factory, _prefix(commitment, '"basis":"')),
        ("COMMITMENT_STRING_UNICODE", commitment_factory, _prefix(commitment, "verificat ă")),
        ("COMMITMENT_TERMINAL", commitment_factory, commitment),
        ("AUTHORITY_INITIAL", authority_factory, ""),
        ("AUTHORITY_DECISION", authority_factory, _prefix(supported, '"decision":"')),
        ("AUTHORITY_REFERENCE_START", authority_factory, _prefix(supported, '"authority_support_ref":')),
        ("AUTHORITY_REFERENCE_HASH", authority_factory, _prefix(supported, context.factual_authority.sha256[:20])),
        ("AUTHORITY_REFERENCE_START_NUMBER", authority_factory, _prefix(supported, '"start_utf8":')),
        ("AUTHORITY_REFERENCE_END_NUMBER", authority_factory, _prefix(supported, '"end_utf8":')),
        ("AUTHORITY_AXIS", authority_factory, _prefix(supported, '"event_axis":"')),
        ("AUTHORITY_FINDING_LINK_SEPARATOR", authority_factory,
         _prefix(unsupported, '"unsupported_finding_ids":["F1"')),
        ("AUTHORITY_FINDING_REASON", authority_factory, _prefix(unsupported, '"reason_code":"')),
        ("AUTHORITY_FINDING_STATUS", authority_factory, _prefix(unsupported, '"reason_status":"')),
        ("AUTHORITY_FIRST_FINDING_SUPPORTING_STATUS", authority_factory,
         _prefix(two_findings, '"reason_status":"')),
        ("AUTHORITY_FINAL_FINDING_DECISIVE_STATUS", authority_factory,
         _prefix_nth(two_findings, '"reason_status":"', 2)),
        ("AUTHORITY_TERMINAL", authority_factory, unsupported),
    ]
    return rows


def main() -> None:
    started = time.perf_counter()
    from transformers import AutoTokenizer, __version__ as transformers_version
    import pydantic

    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    vocabulary_size = len(tokenizer)
    actual_identity = _identity(vocabulary_size)
    if vocabulary_size != EXPECTED_VOCABULARY or actual_identity != EXPECTED_IDENTITY:
        raise SystemExit("TOKENIZER_IDENTITY_MISMATCH")

    context = _context()
    texts = _texts(context)
    matrix = _matrix(context, texts)
    alternate_context = _context()
    from .immutable_source_span_reference_v1 import ImmutableUtf8SourceV1, SourceRoleV1
    from .stage_p_source_reference_constraint_v1 import SourceReferenceConstraintContextV1
    alternate_context = SourceReferenceConstraintContextV1.bind(
        candidate=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data="alt candidat".encode()),
        factual_authority=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY, data="alt authority".encode()),
    )
    from .stage_p_phase2_character_controller_v1 import Phase2AuditLaneV1, Phase2CharacterControllerV1
    left_controller = Phase2CharacterControllerV1(
        lane=Phase2AuditLaneV1.AUTHORITY_RECONCILIATION,
        expected_entry_ids=("P1",), decoder_identity=DECODER_IDENTITY,
        source_context=context)
    right_controller = Phase2CharacterControllerV1(
        lane=Phase2AuditLaneV1.AUTHORITY_RECONCILIATION,
        expected_entry_ids=("P1",), decoder_identity=DECODER_IDENTITY,
        source_context=alternate_context)
    request_context_isolation = (
        left_controller.request_context_identity != right_controller.request_context_identity)
    if not request_context_isolation:
        raise SystemExit("REQUEST_CONTEXT_IDENTITY_ISOLATION_FAILURE")
    special = set(tokenizer.all_special_ids)
    eos = tokenizer.eos_token_id
    pieces = tuple(_decode(tokenizer, (token_id,)) for token_id in range(vocabulary_size))
    empty = {token_id for token_id, piece in enumerate(pieces) if not piece}
    replacement = {token_id for token_id, piece in enumerate(pieces) if "\ufffd" in piece}
    controls = {token_id for token_id, piece in enumerate(pieces)
                if any(ord(char) < 0x20 and char not in "\t\n\r" for char in piece)}
    excluded = (special - {eos}) | empty

    results = []
    false_accepts = false_rejects = contextual_rewrites = suffix_mismatches = 0
    timings = []
    for name, factory, prefix in matrix:
        prefix_ids = tuple(tokenizer.encode(prefix, add_special_tokens=False))
        decoded_prefix = _decode(tokenizer, prefix_ids)
        if decoded_prefix != prefix:
            raise SystemExit(f"PREFIX_ROUNDTRIP_MISMATCH:{name}")
        state = factory().feed(prefix)
        oracle = set()
        context_free = set()
        row_rewrites = row_mismatches = 0
        row_started = time.perf_counter()
        for token_id, piece in enumerate(pieces):
            if token_id in excluded or token_id == eos:
                continue
            decoded_candidate = _decode(tokenizer, (*prefix_ids, token_id))
            if not decoded_candidate.startswith(prefix):
                row_rewrites += 1
                continue
            suffix = decoded_candidate[len(prefix):]
            if suffix != piece:
                row_mismatches += 1
            try:
                state.feed(suffix)
                oracle.add(token_id)
            except ValueError:
                pass
            try:
                state.feed(piece)
                context_free.add(token_id)
            except ValueError:
                pass
        if state.terminal:
            oracle.add(eos)
            context_free.add(eos)
        row_false_accepts = len(context_free - oracle)
        row_false_rejects = len(oracle - context_free)
        elapsed = time.perf_counter() - row_started
        timings.append(elapsed)
        false_accepts += row_false_accepts
        false_rejects += row_false_rejects
        contextual_rewrites += row_rewrites
        suffix_mismatches += row_mismatches
        reference = getattr(state, "reference_state", None)
        results.append({
            "state": name,
            "dfa_mode": "TERMINAL" if state.terminal else state.mode,
            "reference_mode": reference.mode.value if reference else None,
            "allowed_token_count": len(oracle),
            "allowed_token_set_sha256": hashlib.sha256(
                ",".join(map(str, sorted(oracle))).encode()).hexdigest(),
            "sets_equal": oracle == context_free,
            "false_accepts": row_false_accepts,
            "false_rejects": row_false_rejects,
            "contextual_rewrites": row_rewrites,
            "suffix_mismatches": row_mismatches,
            "eos_allowed": eos in oracle,
            "seconds": round(elapsed, 6),
        })

    eos_pass = all(row["eos_allowed"] == (row["dfa_mode"] == "TERMINAL") for row in results)
    exact = not false_accepts and not false_rejects and not contextual_rewrites and not suffix_mismatches
    result = {
        "schema_name": "pastila-semantic-admission-v2-stage-p-phase2-tokenizer-compatibility-audit",
        "schema_version": "1.0.0-evaluation.1",
        "plan_identity": PLAN_IDENTITY,
        "result": ("PASS_CONTEXT_FREE_PIECES_EQUIVALENT_FOR_FROZEN_PHASE2_MATRIX"
                   if exact and eos_pass else "FAIL_CLOSED_PREFIX_SENSITIVE_REQUIRED"),
        "strategy_recommendation": ("CONTEXT_FREE_PIECE_PROJECTION_FEASIBLE_FOR_FROZEN_MATRIX"
                                    if exact and eos_pass else "PREFIX_SENSITIVE_FULL_DECODE_REQUIRED"),
        "completed_phases": list(range(8)),
        "tokenizer": {
            "path": str(MODEL), "identity": actual_identity,
            "vocabulary_size": vocabulary_size,
            "implementation": type(tokenizer).__name__,
            "transformers_version": transformers_version,
            "pydantic_bridge_version": pydantic.__version__,
            "bos_token_id": tokenizer.bos_token_id,
            "eos_token_id": eos,
            "pad_token_id": tokenizer.pad_token_id,
            "unk_token_id": tokenizer.unk_token_id,
            "special_token_ids": sorted(special),
            "empty_decoding_count": len(empty),
            "replacement_character_count": len(replacement),
            "control_decoding_count": len(controls),
        },
        "matrix": {
            "state_count": len(results),
            "candidate_checks": len(results) * vocabulary_size,
            "states": results,
            "false_accepts": false_accepts,
            "false_rejects": false_rejects,
            "contextual_rewrites": contextual_rewrites,
            "standalone_suffix_mismatches": suffix_mismatches,
            "eos_only_at_terminal": eos_pass,
            "special_and_empty_tokens_excluded": True,
            "shortest_start_and_longest_end_reference_covered": True,
            "two_finding_supporting_to_decisive_transition_covered": True,
            "request_context_identity_isolation": request_context_isolation,
        },
        "resource_characterization": {
            "maximum_state_seconds": round(max(timings), 6),
            "median_state_seconds": round(statistics.median(timings), 6),
            "total_elapsed_seconds": round(time.perf_counter() - started, 6),
            "cache_objects_created": 0,
            "cache_identity_requirement": "TOKENIZER_DECODER_REQUEST_CONTEXT_AND_CHARACTER_STATE",
        },
        "warnings": [{
            "reason_code": "EXISTING_MISTRAL_TOKENIZER_REGEX_WARNING",
            "disposition": "PRESERVED_NOT_REPAIRED",
            "effect": "Changing fix_mistral_regex would alter the bound tokenizer contract."
        }],
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "activity": {
            "tokenizer_loads": 1, "tokenizer_decode_calls": len(results) * vocabulary_size,
            "model_loads": 0, "model_calls": 0, "generation_calls": 0,
            "provider_calls": 0, "inference_calls": 0, "projector_objects": 0,
            "evaluator_or_runner_bindings": 0, "probe_constructions": 0,
            "probe_executions": 0,
        },
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if not exact or not eos_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
