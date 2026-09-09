"""Candidate-neutral construction and validation for Semantic Successor V2."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence

from pastila_scout.production_core_semantic_authority_v2 import (
    SYSTEM_INSTRUCTION_V2,
    build_candidate_prompt_v2,
)

PUBLIC_AUTHORITY_REF = (
    "refs/heads/foundation/core-v2-production-core-qualification-framework"
)
PUBLIC_AUTHORITY_COMMIT = "017cc14f8c89dc9039505fb722e1fbd88e3e3c15"
PUBLIC_AUTHORITY_TREE = "5642521282d251d44c6ca308bef121958b23a48d"
UNICODE_AUTHORITY_IDENTITY = (
    "2bc9eb507adfd6d3cb45c6c73d04711e61b0b2f98712daf23ad968de2c30d8fc"
)
SEMANTIC_CONTRACT_IDENTITY = (
    "5ff45b99134e4b4be865949b54202743ef96db276674eefe0185b4f7163b1410"
)
RESPONSE_CONTRACT_IDENTITY = (
    "088ffa8ed7536f732b71b46bdb4f161594518f35a909ea21868044c2902b15e4"
)
CORPUS_IDENTITY = "b67f67147f0e9629189944cf229ffd7da4c03e4b244182d5dce1b808385a9fe9"
ASSERTIONS_IDENTITY = "cce045e9093fb2a92b86339d3f7c7a4e0cd99d85782dc3967826341a7860571c"
RUBRIC_IDENTITY = "659339bac91cfbdf993c7b57555dfd9191e609816db76e60bc41f13d0dfba1a6"
PROFILE_IDENTITY = "06aae46a8dce5eeedbd87cd122e935dcc51e17c221d6efb689b80f20bcda621f"
FRAMEWORK_IDENTITY = "9d8bb34d7ae7a7527ab0916e37a0e0537f156c5b35f7e580e36863efabfbb3c6"
HISTORICAL_CORPUS_IDENTITY = (
    "5933f6ddb450a00566cb42a7dabd908975687360e5d9f16766d55b1dff7899b6"
)
HOLDOUT_IDENTITY = "0a051049c78b893d44968fb02f2df86a3534de803e623ba056d15059a3365c5a"
REGISTRY_IDENTITY = "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
MAX_INPUT_TOKENS = 1924
ROOTFS_SHA256 = "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
BASE_MANIFEST_SHA256 = (
    "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
)
TOKENIZER_SHA256 = "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"
ADAPTER_MANIFESTS = {
    "pastila-editor-core-v1.1-experimental": "0bc4bb1b83b5c1375c1e676844dea079831e7ad0b90db955fa89a2f7d65c3e47",
    "pastila-editor-core-v1.2-experimental": "22b5a7bde7194c66d895b9acab5791a8d8573df67f93704eab933666df7978a2",
}
ALIASES = ("CANDIDATE-A", "CANDIDATE-B")
MATERIALIZATIONS = ("A", "B")
REPETITIONS = (1, 2, 3)
EXPECTED_RUNTIME_CLOSURE_SHA256 = (
    "8657c7d1d0526e64c582f36ae132d24c6efd06928bd87cbe4f74dbaf88f194c3"
)
EXPECTED_EFFECTIVE_TOKENIZER_SHA256 = (
    "7a2235fbe0a3c0caf083a14fb7c9150828927dfb0dc8808abef4568b93bfff7d"
)
EXPECTED_REPOSITORY_SNAPSHOT_SHA256 = (
    "64617e24ebea7f03e49155266add95a01382d6fcc82874e7dff60f4ce3e9e91d"
)
EXPECTED_LAUNCHER_SHA256 = (
    "bcf0e5babf35d3533bd3352630580b1a12eb7e8db3148cce4e348c1b4aa872fb"
)
EXPECTED_PROBE_SHA256 = (
    "b5afad95b2c91e224aaa329fac6dfc20983be8b09b42ddf6ca10b43c74783ccc"
)
EXPECTED_SYSTEM_PROMPT_SHA256 = [
    "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
    "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
]
EXPECTED_TOKEN_COUNT_ROOT = (
    "e24236fbe48fcf74d3f897fd1132518c65fcc0f2c613d9d83c5d07bad34fc9d9"
)


class GenerationAuthorityError(ValueError):
    """The prospective generation escaped frozen V2 authority."""


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_secret_mapping(
    secret: Mapping[str, object], commitment: str
) -> dict[str, str]:
    aliases = secret.get("aliases")
    nonce = secret.get("nonce_hex")
    if (
        tuple(secret) != ("schema", "schema_version", "nonce_hex", "aliases")
        or secret.get("schema") != "pastila-production-core-candidate-alias-secret"
        or secret.get("schema_version") != 1
        or not isinstance(nonce, str)
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
        or not isinstance(aliases, dict)
        or tuple(aliases) != ALIASES
        or set(aliases.values()) != set(ADAPTER_MANIFESTS)
        or hashlib.sha256(canonical(secret)).hexdigest() != commitment
    ):
        raise GenerationAuthorityError("alias secret authority mismatch")
    return {str(key): str(value) for key, value in aliases.items()}


def deterministic_schedule(
    case_ids: Sequence[str], secret: Mapping[str, object], commitment: str
) -> list[dict[str, object]]:
    validate_secret_mapping(secret, commitment)
    if len(case_ids) != 200 or len(set(case_ids)) != 200:
        raise GenerationAuthorityError("case sequence mismatch")
    key = bytes.fromhex(str(secret["nonce_hex"]))
    rows = []
    global_ordinal = 0
    for materialization in MATERIALIZATIONS:
        for repetition in REPETITIONS:
            for alias in ALIASES:
                batch = sorted(
                    (
                        hmac.digest(
                            key,
                            f"{materialization}\0{repetition}\0{alias}\0{case_id}".encode(),
                            "sha256",
                        ),
                        case_id,
                    )
                    for case_id in case_ids
                )
                for batch_ordinal, (_, case_id) in enumerate(batch, 1):
                    global_ordinal += 1
                    rows.append(
                        {
                            "global_ordinal": global_ordinal,
                            "materialization": materialization,
                            "repetition": repetition,
                            "candidate_alias": alias,
                            "batch_ordinal": batch_ordinal,
                            "case_id": case_id,
                        }
                    )
    if len(rows) != 2400:
        raise GenerationAuthorityError("schedule cardinality mismatch")
    return rows


def _unseal(value: Mapping[str, object], key: str, expected: str) -> None:
    core = dict(value)
    recorded = core.pop(key, None)
    if recorded != expected or recorded != identity(core):
        raise GenerationAuthorityError(f"{key} mismatch")


def materialize_request_authorities(
    historical_corpus: Mapping[str, object],
    successor_corpus: Mapping[str, object],
) -> list[dict[str, object]]:
    _unseal(successor_corpus, "corpus_identity", CORPUS_IDENTITY)
    if successor_corpus.get("historical_corpus_identity") != HISTORICAL_CORPUS_IDENTITY:
        raise GenerationAuthorityError("historical case-byte binding mismatch")
    historical_core = dict(historical_corpus)
    historical_recorded = historical_core.pop("corpus_identity", None)
    if (
        historical_recorded != HISTORICAL_CORPUS_IDENTITY
        or historical_recorded != identity(historical_core)
    ):
        raise GenerationAuthorityError("historical corpus mismatch")
    cases = historical_corpus.get("cases")
    authorities = successor_corpus.get("case_authorities")
    if not isinstance(cases, list) or not isinstance(authorities, list):
        raise GenerationAuthorityError("case authority missing")
    if len(cases) != 200 or len(authorities) != 200:
        raise GenerationAuthorityError("case cardinality mismatch")
    by_id = {row.get("case_id"): row for row in authorities if isinstance(row, dict)}
    if len(by_id) != 200:
        raise GenerationAuthorityError("case authority uniqueness mismatch")
    rows: list[dict[str, object]] = []
    for case in cases:
        if not isinstance(case, dict) or case.get("case_id") not in by_id:
            raise GenerationAuthorityError("case authority resolution mismatch")
        authority = by_id[case["case_id"]]
        case_core = dict(case)
        case_recorded = case_core.pop("case_sha256", None)
        if (
            case_recorded != identity(case_core)
            or authority.get("case_sha256") != case_recorded
        ):
            raise GenerationAuthorityError("case byte identity mismatch")
        merged = {
            **case,
            "required_factual_shape": authority.get("required_factual_shape"),
            "expected_material_proposition_count": authority.get(
                "expected_material_proposition_count"
            ),
            "required_commentary_components": authority.get(
                "required_commentary_components"
            ),
        }
        prompt = build_candidate_prompt_v2(merged)
        prompt_bytes = prompt.encode("utf-8")
        rows.append(
            {
                "case_id": case["case_id"],
                "case_sha256": case["case_sha256"],
                "request_identity": case["request_identity"],
                "output_type": case["output_type"],
                "required_factual_shape": merged["required_factual_shape"],
                "expected_material_proposition_count": merged[
                    "expected_material_proposition_count"
                ],
                "required_commentary_components": merged[
                    "required_commentary_components"
                ],
                "candidate_visible_request": prompt,
                "candidate_visible_request_sha256": hashlib.sha256(
                    prompt_bytes
                ).hexdigest(),
                "candidate_visible_request_bytes": len(prompt_bytes),
            }
        )
    if [row["case_id"] for row in rows] != successor_corpus.get("case_ids"):
        raise GenerationAuthorityError("case order mismatch")
    return rows


def validate_generation(
    generation: Mapping[str, object],
    request_manifest: Mapping[str, object],
    candidate_manifest: Mapping[str, object],
    receipts: Mapping[str, Mapping[str, object]],
    historical_corpus: Mapping[str, object],
    successor_corpus: Mapping[str, object],
    secret: Mapping[str, object],
) -> dict[str, str]:
    _unseal(
        generation,
        "qualification_generation_identity",
        str(generation.get("qualification_generation_identity")),
    )
    _unseal(
        request_manifest,
        "request_manifest_identity",
        str(request_manifest.get("request_manifest_identity")),
    )
    expected_requests = materialize_request_authorities(
        historical_corpus, successor_corpus
    )
    if request_manifest != {
        "schema": "pastila-production-core-candidate-request-manifest",
        "schema_version": 2,
        "status": "EXACT_CANDIDATE_VISIBLE_REQUEST_BYTES_PREINFERENCE",
        "public_authority_commit": PUBLIC_AUTHORITY_COMMIT,
        "corpus_identity": CORPUS_IDENTITY,
        "semantic_contract_identity": SEMANTIC_CONTRACT_IDENTITY,
        "structured_response_contract_identity": RESPONSE_CONTRACT_IDENTITY,
        "request_count": 200,
        "requests": expected_requests,
        "candidate_execution_performed": False,
        "request_manifest_identity": request_manifest.get("request_manifest_identity"),
    }:
        raise GenerationAuthorityError("request manifest rederivation mismatch")
    _unseal(
        candidate_manifest,
        "manifest_identity",
        str(candidate_manifest.get("manifest_identity")),
    )
    if candidate_manifest != {
        "schema": "pastila-production-core-candidate-object-manifest",
        "schema_version": 2,
        "status": "UNCHANGED_TECHNICAL_OBJECT_AUTHORITY_NO_EXECUTION",
        "base_model_manifest_sha256": BASE_MANIFEST_SHA256,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizer_fix_mistral_regex": True,
        "adapter_manifest_sha256": ADAPTER_MANIFESTS,
        "rootfs_sha256": ROOTFS_SHA256,
        "candidate_execution_performed": False,
        "manifest_identity": candidate_manifest.get("manifest_identity"),
    }:
        raise GenerationAuthorityError("candidate object authority mismatch")
    expected_receipt_ids = {}
    convergence = None
    for label in MATERIALIZATIONS:
        receipt = receipts.get(label)
        if not isinstance(receipt, Mapping):
            raise GenerationAuthorityError("input receipt absent")
        _unseal(receipt, "receipt_identity", str(receipt.get("receipt_identity")))
        if (
            receipt.get("schema_version") != 2
            or receipt.get("materialization") != label
            or receipt.get("request_manifest_identity")
            != request_manifest.get("request_manifest_identity")
            or receipt.get("tokenizer_sha256") != TOKENIZER_SHA256
            or receipt.get("tokenizer_load_semantics") != "fix_mistral_regex=True"
            or receipt.get("runtime_closure_sha256") != EXPECTED_RUNTIME_CLOSURE_SHA256
            or receipt.get("rootfs_sha256") != ROOTFS_SHA256
            or receipt.get("effective_tokenizer_sha256")
            != EXPECTED_EFFECTIVE_TOKENIZER_SHA256
            or receipt.get("repository_snapshot_sha256")
            != EXPECTED_REPOSITORY_SNAPSHOT_SHA256
            or receipt.get("launcher_sha256") != EXPECTED_LAUNCHER_SHA256
            or receipt.get("probe_sha256") != EXPECTED_PROBE_SHA256
            or receipt.get("candidate_system_prompt_sha256")
            != EXPECTED_SYSTEM_PROMPT_SHA256
            or receipt.get("request_count") != 200
            or receipt.get("rendering_count") != 400
            or receipt.get("input_token_ceiling") != MAX_INPUT_TOKENS
            or type(receipt.get("maximum_input_tokens")) is not int
            or not 0 < int(receipt["maximum_input_tokens"]) <= MAX_INPUT_TOKENS
            or receipt.get("maximum_input_tokens") != 1690
            or receipt.get("attaining_renderings")
            != [[EXPECTED_SYSTEM_PROMPT_SHA256[0], "pcq-rom-011"]]
            or receipt.get("token_count_root") != EXPECTED_TOKEN_COUNT_ROOT
            or receipt.get("model_loaded") is not False
            or receipt.get("inference_executed") is not False
            or receipt.get("candidate_execution_performed") is not False
            or receipt.get("network") != "DENY_ALL_NEW_NAMESPACE"
            or receipt.get("status") != "PASS_ALL_RENDERINGS_WITHIN_1924_TOKENS"
        ):
            raise GenerationAuthorityError("input receipt authority mismatch")
        current = tuple(
            receipt.get(field)
            for field in (
                "runtime_closure_sha256",
                "maximum_input_tokens",
                "attaining_renderings",
                "token_count_root",
            )
        )
        if convergence is not None and current != convergence:
            raise GenerationAuthorityError("input materializations do not converge")
        convergence = current
        expected_receipt_ids[label] = receipt["receipt_identity"]
    bindings = generation.get("authority_bindings")
    expected = {
        "public_ref": PUBLIC_AUTHORITY_REF,
        "public_commit": PUBLIC_AUTHORITY_COMMIT,
        "public_tree": PUBLIC_AUTHORITY_TREE,
        "unicode_authority_identity": UNICODE_AUTHORITY_IDENTITY,
        "semantic_contract_identity": SEMANTIC_CONTRACT_IDENTITY,
        "structured_response_contract_identity": RESPONSE_CONTRACT_IDENTITY,
        "corpus_identity": CORPUS_IDENTITY,
        "assertion_manifest_identity": ASSERTIONS_IDENTITY,
        "rubric_identity": RUBRIC_IDENTITY,
        "execution_profile_identity": PROFILE_IDENTITY,
        "framework_identity": FRAMEWORK_IDENTITY,
        "holdout_identity": HOLDOUT_IDENTITY,
        "adjudicator_registry_identity": REGISTRY_IDENTITY,
    }
    if (
        generation.get("schema_version") != 2
        or generation.get("status") != "FROZEN_PREINFERENCE_CANDIDATE_NEUTRAL"
        or bindings != expected
        or generation.get("request_manifest_identity")
        != request_manifest.get("request_manifest_identity")
        or generation.get("candidate_object_manifest_identity")
        != candidate_manifest.get("manifest_identity")
        or generation.get("input_envelope_receipt_identities") != expected_receipt_ids
        or generation.get("candidate_execution_performed") is not False
        or generation.get("retry_or_redraw_authorized") is not False
    ):
        raise GenerationAuthorityError("generation authority binding mismatch")
    rows = request_manifest.get("requests")
    if not isinstance(rows, list) or len(rows) != 200:
        raise GenerationAuthorityError("request manifest cardinality mismatch")
    for row in rows:
        if not isinstance(row, dict):
            raise GenerationAuthorityError("request row invalid")
        prompt = row.get("candidate_visible_request")
        if not isinstance(prompt, str) or not prompt.startswith(SYSTEM_INSTRUCTION_V2):
            raise GenerationAuthorityError("candidate-visible authority mismatch")
        if hashlib.sha256(prompt.encode()).hexdigest() != row.get(
            "candidate_visible_request_sha256"
        ):
            raise GenerationAuthorityError("request byte mismatch")
    case_ids: Sequence[str] = [str(row["case_id"]) for row in rows]
    commitment = str(generation.get("alias_secret_commitment"))
    schedule = deterministic_schedule(case_ids, secret, commitment)
    if schedule != generation.get("schedule"):
        raise GenerationAuthorityError("schedule mismatch")
    return validate_secret_mapping(secret, commitment)


__all__ = (
    "ADAPTER_MANIFESTS",
    "BASE_MANIFEST_SHA256",
    "ROOTFS_SHA256",
    "TOKENIZER_SHA256",
    "GenerationAuthorityError",
    "deterministic_schedule",
    "identity",
    "materialize_request_authorities",
    "validate_generation",
)
