"""Candidate-neutral authority and durable-record helpers for Core V2 qualification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path

from pastila_scout.production_core_technical_output_envelope_v1 import (
    canonical_response_bytes,
)

HEX = frozenset("0123456789abcdef")
ROOTFS_SHA256 = "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"
BASE_MANIFEST_SHA256 = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
ADAPTER_MANIFESTS = {
    "pastila-editor-core-v1.1-experimental": "0bc4bb1b83b5c1375c1e676844dea079831e7ad0b90db955fa89a2f7d65c3e47",
    "pastila-editor-core-v1.2-experimental": "22b5a7bde7194c66d895b9acab5791a8d8573df67f93704eab933666df7978a2",
}
TOKENIZER_SHA256 = "2a00451398b3bb51d3c0fa3f4758c77061377ada35abbb7f5e1006be3aaced5c"
CORPUS_IDENTITY = "5933f6ddb450a00566cb42a7dabd908975687360e5d9f16766d55b1dff7899b6"
HOLDOUT_IDENTITY = "0a051049c78b893d44968fb02f2df86a3534de803e623ba056d15059a3365c5a"
FREEZE_IDENTITY = "89d13366227b63c29ca71a00426f4918a4d8e62c8e07de10aaa810f887e9611a"
RUBRIC_IDENTITY = "3bff615d5412abbde10a3ab85d45b82a0e019be196ea21914303d1e6b284353b"
REGISTRY_IDENTITY = "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"
PREDECESSOR_ATTEMPT = {
    "schema": "pastila-production-core-comparative-execution-attempt",
    "schema_version": 1,
    "qualification_generation_identity": "69480287640939fbeb9e27c6d0f8b35881a11020baa5a9565f3368fb7ce12155",
    "alias_secret_commitment": "0195c095f520e5cbfbbdbe3f353091ca3cef86e9e3e9862c12dfa9f28267d2e7",
    "attempt_ordinal": 1,
    "retry_or_redraw_authorized": False,
    "status": "CONSUMED_BEFORE_EXECUTION",
    "attempt_identity": "4440016ac96d7d49c6dafd18675b4d6c4a51459a1bc46bc60d7918685845e522",
}
PREDECESSOR_FAILURE = {
    "schema": "pastila-production-core-comparative-execution-terminal-failure",
    "schema_version": 1,
    "qualification_generation_identity": "69480287640939fbeb9e27c6d0f8b35881a11020baa5a9565f3368fb7ce12155",
    "attempt_identity": "4440016ac96d7d49c6dafd18675b4d6c4a51459a1bc46bc60d7918685845e522",
    "failed_materialization": "A",
    "failed_repetition": 1,
    "failed_candidate_alias": "CANDIDATE-A",
    "failure_class": "CalledProcessError",
    "partial_artifact_count": 2,
    "partial_artifact_root": "52296adba2e6d1ba2b4a82047b2b689425423ab2ab8b746010f447631238efff",
    "retry_or_redraw_authorized": False,
    "promotion_effect": False,
    "failure_identity": "0bf4e535ae23b46ef16ba6695a02ec40f6a4c8ba9d4af836593c0626cc2fa708",
}
PRIOR_REPLACEMENT_AUTHORITY = {
    "superseded_generation_identity": "69480287640939fbeb9e27c6d0f8b35881a11020baa5a9565f3368fb7ce12155",
    "consumed_attempt_identity": "4440016ac96d7d49c6dafd18675b4d6c4a51459a1bc46bc60d7918685845e522",
    "terminal_failure_identity": "0bf4e535ae23b46ef16ba6695a02ec40f6a4c8ba9d4af836593c0626cc2fa708",
    "replacement_attempt_ordinal": 2,
    "retry_or_redraw": False,
    "predecessor_attempt": PREDECESSOR_ATTEMPT,
    "predecessor_terminal_failure": PREDECESSOR_FAILURE,
}
PREDECESSOR_ATTEMPT_2 = {
    "schema": "pastila-production-core-comparative-execution-attempt",
    "schema_version": 1,
    "qualification_generation_identity": "870c84ac320153ab20070f2b2106a1dc1c09339d791cf6616b81dc8da0d5c8a6",
    "alias_secret_commitment": "0195c095f520e5cbfbbdbe3f353091ca3cef86e9e3e9862c12dfa9f28267d2e7",
    "attempt_ordinal": 2,
    "retry_or_redraw_authorized": False,
    "status": "CONSUMED_BEFORE_EXECUTION",
    "attempt_identity": "38a82e57df1394e7479ab21da1765f1865f580c4aeb94d875856f9cda115d5df",
}
PREDECESSOR_FAILURE_2 = {
    "schema": "pastila-production-core-comparative-execution-terminal-failure",
    "schema_version": 1,
    "qualification_generation_identity": "870c84ac320153ab20070f2b2106a1dc1c09339d791cf6616b81dc8da0d5c8a6",
    "attempt_identity": "38a82e57df1394e7479ab21da1765f1865f580c4aeb94d875856f9cda115d5df",
    "failed_materialization": "A",
    "failed_repetition": 1,
    "failed_candidate_alias": "CANDIDATE-A",
    "failure_class": "CalledProcessError",
    "partial_artifact_count": 2,
    "partial_artifact_root": "e5261f1648b9675c6b8fe0e23892b0807bb347b811fabb0e9ebe791d5fc3de6e",
    "retry_or_redraw_authorized": False,
    "promotion_effect": False,
    "failure_identity": "5e3fc7a2efb53de28061dc48ed21e04e06d7a6799b09b5f368041d4a26752731",
}
PRIOR_REPLACEMENT_AUTHORITY_2 = {
    "superseded_generation_identity": "870c84ac320153ab20070f2b2106a1dc1c09339d791cf6616b81dc8da0d5c8a6",
    "consumed_attempt_identity": "38a82e57df1394e7479ab21da1765f1865f580c4aeb94d875856f9cda115d5df",
    "terminal_failure_identity": "5e3fc7a2efb53de28061dc48ed21e04e06d7a6799b09b5f368041d4a26752731",
    "replacement_attempt_ordinal": 3,
    "retry_or_redraw": False,
    "predecessor_attempt": PREDECESSOR_ATTEMPT_2,
    "predecessor_terminal_failure": PREDECESSOR_FAILURE_2,
    "prior_replacement_authority": PRIOR_REPLACEMENT_AUTHORITY,
}
PREDECESSOR_ATTEMPT_3 = {
    "schema": "pastila-production-core-comparative-execution-attempt",
    "schema_version": 1,
    "qualification_generation_identity": "6ebd356f7e42ca8192f4e362127f17f169337d24923274dad472b5e43f3509cb",
    "alias_secret_commitment": "0195c095f520e5cbfbbdbe3f353091ca3cef86e9e3e9862c12dfa9f28267d2e7",
    "attempt_ordinal": 3,
    "retry_or_redraw_authorized": False,
    "status": "CONSUMED_BEFORE_EXECUTION",
    "attempt_identity": "bd2710eeb4c22e7d3232e2566c61ac94f12c862ead418fc615efbb11d32de1c9",
}
PREDECESSOR_FAILURE_3 = {
    "schema": "pastila-production-core-comparative-execution-terminal-failure",
    "schema_version": 1,
    "qualification_generation_identity": "6ebd356f7e42ca8192f4e362127f17f169337d24923274dad472b5e43f3509cb",
    "attempt_identity": "bd2710eeb4c22e7d3232e2566c61ac94f12c862ead418fc615efbb11d32de1c9",
    "failed_materialization": "A",
    "failed_repetition": 1,
    "failed_candidate_alias": "CANDIDATE-A",
    "failure_class": "CalledProcessError",
    "partial_artifact_count": 8,
    "partial_artifact_root": "e1818e65a4c63373f3a0f2ead6519da651ec4875f9db6d4ca34d1062f5716cd8",
    "retry_or_redraw_authorized": False,
    "promotion_effect": False,
    "failure_identity": "9bb7a9258348428b3f7d9aa8d2c6235ca68418a2f5879f89c4cd2ce818bb2d0e",
}
PRIOR_REPLACEMENT_AUTHORITY_3 = {
    "superseded_generation_identity": "6ebd356f7e42ca8192f4e362127f17f169337d24923274dad472b5e43f3509cb",
    "consumed_attempt_identity": "bd2710eeb4c22e7d3232e2566c61ac94f12c862ead418fc615efbb11d32de1c9",
    "terminal_failure_identity": "9bb7a9258348428b3f7d9aa8d2c6235ca68418a2f5879f89c4cd2ce818bb2d0e",
    "replacement_attempt_ordinal": 4,
    "retry_or_redraw": False,
    "predecessor_attempt": PREDECESSOR_ATTEMPT_3,
    "predecessor_terminal_failure": PREDECESSOR_FAILURE_3,
    "prior_replacement_authority": PRIOR_REPLACEMENT_AUTHORITY_2,
}
PREDECESSOR_ATTEMPT_4 = {
    "schema": "pastila-production-core-comparative-execution-attempt",
    "schema_version": 1,
    "qualification_generation_identity": "80058a04ee40c896a71c950b83c242af160479fcce5bd495577c57cea9d0bc04",
    "alias_secret_commitment": "0195c095f520e5cbfbbdbe3f353091ca3cef86e9e3e9862c12dfa9f28267d2e7",
    "attempt_ordinal": 4,
    "retry_or_redraw_authorized": False,
    "status": "CONSUMED_BEFORE_EXECUTION",
    "attempt_identity": "cc6d9969c6f2392cbe76c4068becd1e049226dcadf61f4e3eb0f93bec2d65aad",
}
PREDECESSOR_FAILURE_4 = {
    "schema": "pastila-production-core-comparative-execution-terminal-failure",
    "schema_version": 1,
    "qualification_generation_identity": "80058a04ee40c896a71c950b83c242af160479fcce5bd495577c57cea9d0bc04",
    "attempt_identity": "cc6d9969c6f2392cbe76c4068becd1e049226dcadf61f4e3eb0f93bec2d65aad",
    "failed_materialization": "A",
    "failed_repetition": 1,
    "failed_candidate_alias": "CANDIDATE-A",
    "failure_class": "CalledProcessError",
    "partial_artifact_count": 188,
    "partial_artifact_root": "43448503978ceba8118450b71c7ec4effe462926cdab4e2816fa2149ef922aa6",
    "retry_or_redraw_authorized": False,
    "promotion_effect": False,
    "failure_identity": "2669611fca5cd76ce84aad37d737f139c26cc65c452bceed350257d405811c6c",
}
PRIOR_REPLACEMENT_AUTHORITY_4 = {
    "superseded_generation_identity": "80058a04ee40c896a71c950b83c242af160479fcce5bd495577c57cea9d0bc04",
    "consumed_attempt_identity": "cc6d9969c6f2392cbe76c4068becd1e049226dcadf61f4e3eb0f93bec2d65aad",
    "terminal_failure_identity": "2669611fca5cd76ce84aad37d737f139c26cc65c452bceed350257d405811c6c",
    "replacement_attempt_ordinal": 5,
    "retry_or_redraw": False,
    "predecessor_attempt": PREDECESSOR_ATTEMPT_4,
    "predecessor_terminal_failure": PREDECESSOR_FAILURE_4,
    "prior_replacement_authority": PRIOR_REPLACEMENT_AUTHORITY_3,
}
PREDECESSOR_ATTEMPT_5 = {
    "schema": "pastila-production-core-comparative-execution-attempt",
    "schema_version": 1,
    "qualification_generation_identity": "254525ca4dbd811a2fc0108c5a5c4b967be84e9cea36a855a46a55396cbecce6",
    "alias_secret_commitment": "0195c095f520e5cbfbbdbe3f353091ca3cef86e9e3e9862c12dfa9f28267d2e7",
    "attempt_ordinal": 5,
    "retry_or_redraw_authorized": False,
    "status": "CONSUMED_BEFORE_EXECUTION",
    "attempt_identity": "baa40e694c51377ba3f8a97ff9eefcf80d17704e1ad2c8830acf2cefa6875842",
}
PREDECESSOR_FAILURE_5 = {
    "schema": "pastila-production-core-comparative-execution-terminal-failure",
    "schema_version": 1,
    "qualification_generation_identity": "254525ca4dbd811a2fc0108c5a5c4b967be84e9cea36a855a46a55396cbecce6",
    "attempt_identity": "baa40e694c51377ba3f8a97ff9eefcf80d17704e1ad2c8830acf2cefa6875842",
    "failed_materialization": "A",
    "failed_repetition": 1,
    "failed_candidate_alias": "CANDIDATE-A",
    "failure_class": "CalledProcessError",
    "partial_artifact_count": 104,
    "partial_artifact_root": "8c4127bc2561f42eb738a19909a49e3c37326eac81b51fceb581301dca86295b",
    "retry_or_redraw_authorized": False,
    "promotion_effect": False,
    "failure_identity": "ee2cdd079d3879e6760804108bc11c8e805a7271fd694a29fc164dabdee13778",
}
REPLACEMENT_AUTHORITY = {
    "superseded_generation_identity": "254525ca4dbd811a2fc0108c5a5c4b967be84e9cea36a855a46a55396cbecce6",
    "consumed_attempt_identity": "baa40e694c51377ba3f8a97ff9eefcf80d17704e1ad2c8830acf2cefa6875842",
    "terminal_failure_identity": "ee2cdd079d3879e6760804108bc11c8e805a7271fd694a29fc164dabdee13778",
    "replacement_attempt_ordinal": 6,
    "retry_or_redraw": False,
    "predecessor_attempt": PREDECESSOR_ATTEMPT_5,
    "predecessor_terminal_failure": PREDECESSOR_FAILURE_5,
    "prior_replacement_authority": PRIOR_REPLACEMENT_AUTHORITY_4,
}
PREDECESSOR_ATTEMPT_6 = {
    "schema": "pastila-production-core-comparative-execution-attempt",
    "schema_version": 1,
    "qualification_generation_identity": "b865af83fe360eb19c4f1fe07ad953becf38daedf6282e7c4f85027dc649eeac",
    "alias_secret_commitment": "0195c095f520e5cbfbbdbe3f353091ca3cef86e9e3e9862c12dfa9f28267d2e7",
    "attempt_ordinal": 6,
    "retry_or_redraw_authorized": False,
    "status": "CONSUMED_BEFORE_EXECUTION",
    "attempt_identity": "fe679550cc192134c4f3a756e497521285a7dc52d0473e92ba6f68025a9b64c5",
}
PREDECESSOR_FAILURE_6 = {
    "schema": "pastila-production-core-comparative-execution-terminal-failure",
    "schema_version": 1,
    "qualification_generation_identity": "b865af83fe360eb19c4f1fe07ad953becf38daedf6282e7c4f85027dc649eeac",
    "attempt_identity": "fe679550cc192134c4f3a756e497521285a7dc52d0473e92ba6f68025a9b64c5",
    "failure_class": "UNCAUGHT_OR_CANCELLED_AFTER_ATTEMPT_CONSUMPTION",
    "partial_artifact_count": 406,
    "partial_artifact_root": "9626f2628183e8137be37d9ffed5b3018d4b323cf69f66a47626f9cc87095dc4",
    "retry_or_redraw_authorized": False,
    "promotion_effect": False,
    "failure_identity": "1f507b9ddc7470891e41f440cbe8306ebaa3dcf47db4b79e13956641dc1fe9c5",
}
REPLACEMENT_AUTHORITY_7 = {
    "superseded_generation_identity": "b865af83fe360eb19c4f1fe07ad953becf38daedf6282e7c4f85027dc649eeac",
    "consumed_attempt_identity": "fe679550cc192134c4f3a756e497521285a7dc52d0473e92ba6f68025a9b64c5",
    "terminal_failure_identity": "1f507b9ddc7470891e41f440cbe8306ebaa3dcf47db4b79e13956641dc1fe9c5",
    "replacement_attempt_ordinal": 7,
    "retry_or_redraw": False,
    "predecessor_attempt": PREDECESSOR_ATTEMPT_6,
    "predecessor_terminal_failure": PREDECESSOR_FAILURE_6,
    "prior_replacement_authority": REPLACEMENT_AUTHORITY,
}
MATERIALIZATIONS = ("A", "B")
REPETITIONS = (1, 2, 3)
ALIASES = ("CANDIDATE-A", "CANDIDATE-B")
MAX_INPUT_TOKENS = 1924
MAX_OUTPUT_TOKENS = 6268
TOTAL_CONTEXT_TOKENS = 8192
WALL_TIME_NS = 600_000_000_000
PEAK_RSS_BYTES = 16_106_127_360


class QualificationAuthorityError(ValueError):
    """A qualification input or durable result escaped frozen authority."""


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def identity(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def file_manifest(root: Path) -> tuple[str, int, int]:
    """Hash an exact flat model/adapter directory without following links."""
    resolved = root.resolve(strict=True)
    if root.is_symlink() or not resolved.is_dir():
        raise QualificationAuthorityError("candidate object root is invalid")
    records: list[bytes] = []
    total = 0
    for entry in sorted(resolved.iterdir(), key=lambda item: item.name.encode("utf-8")):
        if entry.is_symlink() or not entry.is_file() or entry.parent != resolved:
            raise QualificationAuthorityError("candidate object is not a closed flat directory")
        data = entry.read_bytes()
        records.append(
            entry.name.encode("utf-8")
            + b"\0"
            + len(data).to_bytes(8, "big")
            + hashlib.sha256(data).digest()
        )
        total += len(data)
    if not records:
        raise QualificationAuthorityError("candidate object is empty")
    return hashlib.sha256(b"".join(records)).hexdigest(), total, len(records)


def validate_secret_mapping(secret: Mapping[str, object], commitment: str) -> dict[str, str]:
    if list(secret) != ["schema", "schema_version", "nonce_hex", "aliases"]:
        raise QualificationAuthorityError("alias secret schema/order mismatch")
    nonce = secret["nonce_hex"]
    aliases = secret["aliases"]
    if (
        secret["schema"] != "pastila-production-core-candidate-alias-secret"
        or secret["schema_version"] != 1
        or not isinstance(nonce, str)
        or len(nonce) != 64
        or any(ch not in HEX for ch in nonce)
        or not isinstance(aliases, dict)
        or list(aliases) != list(ALIASES)
        or set(aliases.values()) != set(ADAPTER_MANIFESTS)
        or hashlib.sha256(canonical_json_bytes(secret)).hexdigest() != commitment
    ):
        raise QualificationAuthorityError("alias secret authority mismatch")
    return {str(key): str(value) for key, value in aliases.items()}


def deterministic_schedule(
    case_ids: Sequence[str], secret: Mapping[str, object], commitment: str
) -> list[dict[str, object]]:
    validate_secret_mapping(secret, commitment)
    if len(case_ids) != 200 or len(set(case_ids)) != 200:
        raise QualificationAuthorityError("corpus case sequence is not a closed unique set")
    key = bytes.fromhex(str(secret["nonce_hex"]))
    rows: list[dict[str, object]] = []
    global_ordinal = 0
    for materialization in MATERIALIZATIONS:
        for repetition in REPETITIONS:
            for alias in ALIASES:
                batch: list[tuple[bytes, str]] = []
                for case_id in case_ids:
                    label = f"{materialization}\0{repetition}\0{alias}\0{case_id}".encode()
                    batch.append((hmac.digest(key, label, "sha256"), case_id))
                for ordinal, (_, case_id) in enumerate(sorted(batch), 1):
                    global_ordinal += 1
                    rows.append(
                        {
                            "global_ordinal": global_ordinal,
                            "materialization": materialization,
                            "repetition": repetition,
                            "candidate_alias": alias,
                            "batch_ordinal": ordinal,
                            "case_id": case_id,
                        }
                    )
    if len(rows) != 2400:
        raise QualificationAuthorityError("qualification matrix cardinality mismatch")
    return rows


SYSTEM_INSTRUCTION = (
    "Return exactly one Structured Qualification Response V1 JSON object and EOF. "
    "Use exactly these ordered keys: schema,schema_version,case_id,request_identity,"
    "output_type,outcome,text,claim_bindings,abstention_code. Never add, repair, "
    "truncate, retry, redraw, or emit trailing text. Bind factual claims only to supplied "
    "source_span_ids. Fail closed with an authorized abstention code when authority is "
    "insufficient or the request cannot satisfy the contract."
)


def build_candidate_prompt(case: Mapping[str, object]) -> str:
    exact = {
        "case_id": case["case_id"],
        "request_identity": case["request_identity"],
        "output_type": case["output_type"],
        "request": case["request"],
        "authority_spans": case["authority_spans"],
    }
    return SYSTEM_INSTRUCTION + "\nINPUT=" + canonical_json_bytes(exact).decode("utf-8")


def validate_generation_authority(
    plan: Mapping[str, object], candidate_manifest: Mapping[str, object],
    corpus: Mapping[str, object], secret: Mapping[str, object],
) -> dict[str, str]:
    """Close the public plan over its local secret and frozen corpus before launch."""
    if list(plan)[-1:] != ["qualification_generation_identity"]:
        raise QualificationAuthorityError("generation field order mismatch")
    core = dict(plan)
    recorded = core.pop("qualification_generation_identity", None)
    if recorded != identity(core):
        raise QualificationAuthorityError("generation identity mismatch")
    replacement = plan.get("replacement_authority")
    if not isinstance(replacement, dict):
        raise QualificationAuthorityError("replacement authority absent")
    attempt = replacement.get("predecessor_attempt")
    failure = replacement.get("predecessor_terminal_failure")
    if not isinstance(attempt, dict) or not isinstance(failure, dict):
        raise QualificationAuthorityError("replacement evidence absent")
    attempt_core = dict(attempt)
    attempt_identity = attempt_core.pop("attempt_identity", None)
    failure_core = dict(failure)
    failure_identity = failure_core.pop("failure_identity", None)
    if (
        attempt_identity != identity(attempt_core)
        or failure_identity != identity(failure_core)
        or failure.get("attempt_identity") != attempt_identity
        or failure.get("qualification_generation_identity")
        != attempt.get("qualification_generation_identity")
    ):
        raise QualificationAuthorityError("replacement evidence identity mismatch")
    if list(candidate_manifest)[-1:] != ["manifest_identity"]:
        raise QualificationAuthorityError("candidate manifest field order mismatch")
    manifest_core = dict(candidate_manifest)
    manifest_identity = manifest_core.pop("manifest_identity", None)
    if manifest_identity != identity(manifest_core):
        raise QualificationAuthorityError("candidate manifest identity mismatch")
    if (
        plan.get("status") != "FROZEN_BEFORE_FIRST_SEMANTIC_CANDIDATE_INFERENCE"
        or plan.get("corpus_identity") != CORPUS_IDENTITY
        or plan.get("holdout_identity") != HOLDOUT_IDENTITY
        or plan.get("freeze_identity") != FREEZE_IDENTITY
        or plan.get("rubric_identity") != RUBRIC_IDENTITY
        or plan.get("adjudicator_registry_identity") != REGISTRY_IDENTITY
        or plan.get("candidate_object_manifest_identity") != manifest_identity
        or plan.get("replacement_authority") != REPLACEMENT_AUTHORITY_7
        or plan.get("candidate_execution_performed") is not False
        or plan.get("promotion_effect") is not False
    ):
        raise QualificationAuthorityError("generation authority binding mismatch")
    if (
        candidate_manifest.get("base_model")
        != {"manifest_sha256": BASE_MANIFEST_SHA256, "bytes": 27924394330, "files": 17}
        or candidate_manifest.get("tokenizer")
        != {"object_sha256": TOKENIZER_SHA256, "fix_mistral_regex": True}
        or candidate_manifest.get("rootfs_sha256") != ROOTFS_SHA256
        or candidate_manifest.get("candidate_execution_performed") is not False
    ):
        raise QualificationAuthorityError("candidate object authority mismatch")
    adapters = candidate_manifest.get("adapters")
    if not isinstance(adapters, dict) or {
        key: value.get("manifest_sha256") if isinstance(value, dict) else None
        for key, value in adapters.items()
    } != ADAPTER_MANIFESTS:
        raise QualificationAuthorityError("adapter manifest closure mismatch")
    cases = corpus.get("cases")
    if corpus.get("corpus_identity") != CORPUS_IDENTITY or not isinstance(cases, list):
        raise QualificationAuthorityError("corpus authority mismatch")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    expected = deterministic_schedule(case_ids, secret, str(plan.get("alias_secret_commitment")))
    if plan.get("schedule") != expected:
        raise QualificationAuthorityError("schedule does not derive from frozen secret/corpus")
    return validate_secret_mapping(secret, str(plan.get("alias_secret_commitment")))


def materialize_batches(
    plan: Mapping[str, object], candidate_manifest: Mapping[str, object],
    corpus: Mapping[str, object], secret: Mapping[str, object],
) -> list[dict[str, object]]:
    """Derive the only twelve executable batches; no caller-selected cases."""
    mapping = validate_generation_authority(plan, candidate_manifest, corpus, secret)
    by_id = {case["case_id"]: case for case in corpus["cases"]}  # type: ignore[index]
    batches: list[dict[str, object]] = []
    for materialization in MATERIALIZATIONS:
        for repetition in REPETITIONS:
            for alias in ALIASES:
                rows = [
                    row for row in plan["schedule"]  # type: ignore[index]
                    if row["materialization"] == materialization
                    and row["repetition"] == repetition
                    and row["candidate_alias"] == alias
                ]
                payload = [
                    {
                        "case_id": row["case_id"],
                        "request_identity": by_id[row["case_id"]]["request_identity"],
                        "prompt": build_candidate_prompt(by_id[row["case_id"]]),
                    }
                    for row in rows
                ]
                batches.append(
                    {
                        "materialization": materialization,
                        "repetition": repetition,
                        "candidate_alias": alias,
                        "candidate": mapping[alias],
                        "batch": payload,
                        "batch_sha256": hashlib.sha256(canonical_json_bytes(payload)).hexdigest(),
                    }
                )
    if len(batches) != 12 or any(len(batch["batch"]) != 200 for batch in batches):  # type: ignore[arg-type]
        raise QualificationAuthorityError("derived batch closure mismatch")
    return batches


def validate_candidate_output(raw: bytes, case: Mapping[str, object]) -> tuple[dict[str, object], bytes]:
    if len(raw) > 6268 or raw.startswith(b"\xef\xbb\xbf") or raw.endswith(b"\n"):
        raise QualificationAuthorityError("raw output framing/byte ceiling invalid")
    try:
        parsed = json.loads(raw.decode("utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise QualificationAuthorityError("candidate output is not one UTF-8 JSON object") from exc
    if not isinstance(parsed, dict):
        raise QualificationAuthorityError("candidate output is not an object")
    try:
        canonical = canonical_response_bytes(parsed)
    except (KeyError, TypeError, ValueError, UnicodeEncodeError) as exc:
        raise QualificationAuthorityError(
            "candidate output violates structured response contract"
        ) from exc
    if raw != canonical:
        raise QualificationAuthorityError("candidate output is not canonical or contains trailing bytes")
    if parsed["case_id"] != case["case_id"] or parsed["request_identity"] != case["request_identity"]:
        raise QualificationAuthorityError("candidate output request binding mismatch")
    if parsed["output_type"] != case["output_type"]:
        raise QualificationAuthorityError("candidate output type mismatch")
    return parsed, canonical


def build_execution_receipt(
    *, authority: Mapping[str, object], schedule_row: Mapping[str, object],
    raw_output: bytes, output_tokens: int, input_tokens: int,
    load_plus_generation_wall_ns: int, peak_rss_bytes: int,
    network_log_sha256: str, file_access_log_sha256: str,
    observation_sha256: str, observation_identity: str,
    runner_sha256: str, prompt_sha256: str, batch_sha256: str,
    candidate: str, terminal_eos: bool,
) -> dict[str, object]:
    integers = (output_tokens, input_tokens, load_plus_generation_wall_ns, peak_rss_bytes)
    if any(type(value) is not int or value < 0 for value in integers):
        raise QualificationAuthorityError("measurement is invalid")
    if (
        input_tokens > MAX_INPUT_TOKENS
        or output_tokens > MAX_OUTPUT_TOKENS
        or input_tokens + output_tokens > TOTAL_CONTEXT_TOKENS
        or load_plus_generation_wall_ns > WALL_TIME_NS
        or peak_rss_bytes > PEAK_RSS_BYTES
    ):
        raise QualificationAuthorityError("qualification execution envelope exceeded")
    for value in (
        network_log_sha256, file_access_log_sha256, observation_sha256,
        observation_identity, runner_sha256, prompt_sha256, batch_sha256,
    ):
        if len(value) != 64 or any(ch not in HEX for ch in value):
            raise QualificationAuthorityError("log identity invalid")
    if candidate not in ADAPTER_MANIFESTS or type(terminal_eos) is not bool:
        raise QualificationAuthorityError("candidate receipt authority invalid")
    core = {
        "schema": "pastila-production-core-candidate-execution-receipt",
        "schema_version": 1,
        "qualification_generation_identity": authority["qualification_generation_identity"],
        "schedule_row": dict(schedule_row),
        "raw_output_sha256": hashlib.sha256(raw_output).hexdigest(),
        "raw_output_bytes": len(raw_output),
        "observation_sha256": observation_sha256,
        "observation_identity": observation_identity,
        "rootfs_sha256": ROOTFS_SHA256,
        "base_manifest_sha256": BASE_MANIFEST_SHA256,
        "adapter_manifest_sha256": ADAPTER_MANIFESTS[candidate],
        "tokenizer_sha256": TOKENIZER_SHA256,
        "runner_sha256": runner_sha256,
        "system_prompt_sha256": prompt_sha256,
        "batch_sha256": batch_sha256,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "load_plus_generation_wall_ns": load_plus_generation_wall_ns,
        "peak_rss_bytes": peak_rss_bytes,
        "network_policy": "DENY_ALL_NEW_CHILD_NAMESPACE",
        "network_log_sha256": network_log_sha256,
        "file_access_log_sha256": file_access_log_sha256,
        "terminal_eos": terminal_eos,
        "promotion_effect": False,
    }
    return {**core, "receipt_identity": identity(core)}


def build_blind_packet(
    *, authority: Mapping[str, object], case: Mapping[str, object], alias: str,
    raw_output: bytes, assertion: Mapping[str, object], rubric: Mapping[str, object],
    execution_receipt_identity: str | None = None,
    terminal_eos: bool = True,
) -> dict[str, object]:
    if alias not in ALIASES:
        raise QualificationAuthorityError("candidate alias invalid")
    if execution_receipt_identity is not None and (
        len(execution_receipt_identity) != 64
        or any(ch not in HEX for ch in execution_receipt_identity)
    ):
        raise QualificationAuthorityError("execution receipt identity invalid")
    if type(terminal_eos) is not bool:
        raise QualificationAuthorityError("terminal EOS authority invalid")
    raw_sha256 = hashlib.sha256(raw_output).hexdigest()
    try:
        if not terminal_eos:
            raise QualificationAuthorityError("candidate output did not terminate with EOS")
        parsed, canonical = validate_candidate_output(raw_output, case)
    except QualificationAuthorityError as exc:
        parsed = None
        validation = {
            "status": "FAIL",
            "failure_code": "STRUCTURED_RESPONSE_V1_INVALID",
            "failure_detail": str(exc),
        }
    else:
        if canonical != raw_output:
            raise QualificationAuthorityError("validated output byte identity changed")
        validation = {
            "status": "PASS",
            "failure_code": None,
            "failure_detail": None,
        }
    core = {
        "schema": "pastila-production-core-blind-adjudication-packet",
        "schema_version": 1,
        "qualification_generation_sha256": authority["qualification_generation_identity"],
        "corpus_sha256": CORPUS_IDENTITY,
        "case": dict(case),
        "candidate_alias": alias,
        "candidate_output": parsed,
        "candidate_output_base64": base64.b64encode(raw_output).decode("ascii"),
        "candidate_output_sha256": raw_sha256,
        "candidate_output_validation": validation,
        "execution_receipt_identity": execution_receipt_identity,
        "assertion": dict(assertion),
        "rubric_sha256": RUBRIC_IDENTITY,
        "adjudicator_registry_identity": REGISTRY_IDENTITY,
    }
    return {**core, "packet_identity": identity(core)}


def semantic_adjudication_authority(
    packet: Mapping[str, object],
) -> dict[str, object]:
    """Issue semantic authority only for a structurally valid blinded packet."""

    core = dict(packet)
    packet_identity = core.pop("packet_identity", None)
    if packet_identity != identity(core):
        raise QualificationAuthorityError("blind packet identity mismatch")
    validation = packet.get("candidate_output_validation")
    if not isinstance(validation, dict) or validation.get("status") != "PASS":
        raise QualificationAuthorityError("structural FAIL is terminal")
    if validation != {"status": "PASS", "failure_code": None, "failure_detail": None}:
        raise QualificationAuthorityError("structural validation authority invalid")
    return {
        "qualification_generation_sha256": packet["qualification_generation_sha256"],
        "corpus_sha256": packet["corpus_sha256"],
        "case_id": packet["case"]["case_id"],  # type: ignore[index]
        "candidate_alias": packet["candidate_alias"],
        "candidate_output_sha256": packet["candidate_output_sha256"],
        "assertion_id": packet["assertion"]["assertion_id"],  # type: ignore[index]
        "rubric_sha256": packet["rubric_sha256"],
        "adjudicator_registry_identity": packet["adjudicator_registry_identity"],
    }


def atomic_publish(path: Path, data: bytes) -> None:
    parent = path.parent.resolve(strict=True)
    if path.exists() or path.is_symlink() or path.parent.resolve(strict=True) != parent:
        raise QualificationAuthorityError("durable output target is not new and contained")
    fd = os.open(parent, os.O_RDONLY) if os.name != "nt" else None
    try:
        temporary = parent / f".{path.name}.{os.getpid()}.tmp"
        if temporary.exists() or temporary.is_symlink():
            raise QualificationAuthorityError("durable temporary target collision")
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if fd is not None:
            os.fsync(fd)
    finally:
        if fd is not None:
            os.close(fd)


__all__ = (
    "ADAPTER_MANIFESTS",
    "BASE_MANIFEST_SHA256",
    "CORPUS_IDENTITY",
    "FREEZE_IDENTITY",
    "HOLDOUT_IDENTITY",
    "REPLACEMENT_AUTHORITY_7",
    "ROOTFS_SHA256",
    "TOKENIZER_SHA256",
    "QualificationAuthorityError",
    "atomic_publish",
    "build_blind_packet",
    "build_candidate_prompt",
    "build_execution_receipt",
    "canonical_json_bytes",
    "deterministic_schedule",
    "file_manifest",
    "identity",
    "materialize_batches",
    "semantic_adjudication_authority",
    "validate_candidate_output",
    "validate_generation_authority",
    "validate_secret_mapping",
)
