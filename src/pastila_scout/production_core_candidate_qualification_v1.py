"""Candidate-neutral authority and durable-record helpers for Core V2 qualification."""

from __future__ import annotations

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
    canonical = canonical_response_bytes(parsed)
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
    candidate: str,
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
    if candidate not in ADAPTER_MANIFESTS:
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
        "terminal_eos": True,
        "promotion_effect": False,
    }
    return {**core, "receipt_identity": identity(core)}


def build_blind_packet(
    *, authority: Mapping[str, object], case: Mapping[str, object], alias: str,
    raw_output: bytes, assertion: Mapping[str, object], rubric: Mapping[str, object],
    execution_receipt_identity: str | None = None,
) -> dict[str, object]:
    if alias not in ALIASES:
        raise QualificationAuthorityError("candidate alias invalid")
    if execution_receipt_identity is not None and (
        len(execution_receipt_identity) != 64
        or any(ch not in HEX for ch in execution_receipt_identity)
    ):
        raise QualificationAuthorityError("execution receipt identity invalid")
    parsed, canonical = validate_candidate_output(raw_output, case)
    core = {
        "schema": "pastila-production-core-blind-adjudication-packet",
        "schema_version": 1,
        "qualification_generation_sha256": authority["qualification_generation_identity"],
        "corpus_sha256": CORPUS_IDENTITY,
        "case": dict(case),
        "candidate_alias": alias,
        "candidate_output": parsed,
        "candidate_output_sha256": hashlib.sha256(canonical).hexdigest(),
        "execution_receipt_identity": execution_receipt_identity,
        "assertion": dict(assertion),
        "rubric_sha256": RUBRIC_IDENTITY,
        "adjudicator_registry_identity": REGISTRY_IDENTITY,
    }
    return {**core, "packet_identity": identity(core)}


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
    "validate_candidate_output",
    "validate_generation_authority",
    "validate_secret_mapping",
)
